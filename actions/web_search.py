#web_search.py
import json
import sys
import threading
import time
from pathlib import Path

def _safe_print(text: str) -> None:
    try:
        print(text)
    except Exception:
        try:
            print(text.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

# ── Gemini grounding quota circuit breaker ────────────────────────────────────
# The google_search grounding tool has its own small quota, separate from plain
# generation.  Once it is spent every call returns 429 — so retrying it at the
# top of every search only adds a dead round-trip before the DDG fallback runs.
# After a quota error, skip Gemini entirely for a cooldown period.
_QUOTA_COOLDOWN_SEC  = 900          # 15 minutes
_quota_blocked_until = 0.0
_quota_lock          = threading.Lock()


def _gemini_available() -> bool:
    with _quota_lock:
        return time.monotonic() >= _quota_blocked_until


def _note_gemini_error(exc: Exception) -> None:
    """Trip the breaker when the error is a quota / rate-limit rejection."""
    global _quota_blocked_until
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        with _quota_lock:
            already = time.monotonic() < _quota_blocked_until
            _quota_blocked_until = time.monotonic() + _QUOTA_COOLDOWN_SEC
        if not already:
            _safe_print(
                "[WebSearch] Gemini grounding quota exhausted — skipping it for "
                f"{_QUOTA_COOLDOWN_SEC // 60} min and serving results from DDG."
            )


class _QuotaCooldown(RuntimeError):
    """Raised instead of calling Gemini while the quota breaker is open."""


def _log_gemini_failure(context: str, exc: Exception) -> None:
    """Log a Gemini failure — silently when it is just the expected cooldown."""
    if isinstance(exc, _QuotaCooldown):
        return          # announced once when the breaker tripped; not a warning
    _safe_print(f"[WebSearch] ⚠️ {context} failed ({exc}) — using DDG instead")


def _run_bounded(fn, timeout: float, label: str = "task"):
    """Run fn() in a daemon thread; return its result, or None if it overruns."""
    box = [None]

    def _run():
        try:
            box[0] = fn()
        except Exception as e:
            _log_gemini_failure(label, e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f"[WebSearch] {label} exceeded {timeout:.0f}s — moving on")
    return box[0]

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _gemini_search(query: str) -> str:
    if not _gemini_available():
        raise _QuotaCooldown("Gemini grounding is in quota cooldown")

    from core import gemini

    # Grounded search reads a live page, so it gets a longer deadline than the
    # default — but it still HAS one, and it still walks the fallback ladder.
    try:
        response = gemini.call(query, tier=gemini.SEARCH,
                               config={"tools": [{"google_search": {}}]},
                               timeout_ms=30_000)
        if response is None:
            raise RuntimeError("every Gemini model on the ladder failed")
    except Exception as e:
        _note_gemini_error(e)
        raise

    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


# ── Tavily AI Search (Tier 1 — Ultra-Fast REST API) ─────────────────────────

def _tavily_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 6,
    topic: str = "general",
    timeout: float = 3.0,
) -> list[dict]:
    """Execute low-latency direct query against Tavily AI Search REST API (zero PyPI deps)."""
    from memory.config_manager import get_tavily_api_key
    api_key = get_tavily_api_key()
    if not api_key:
        return []

    import urllib.request
    import urllib.error

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "topic": topic,
        "include_answer": True,
    }
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json", "User-Agent": "ZEZO-OS/2.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                results = []
                # Include Tavily AI direct synthesis answer if provided
                ai_answer = raw_data.get("answer")
                for r in raw_data.get("results", []):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("content", ""),
                        "url": r.get("url", ""),
                        "score": r.get("score", 0.0),
                        "answer": ai_answer,
                    })
                return results
    except Exception as e:
        _safe_print(f"[WebSearch] ⚠️ Tavily search failed ({e}) — falling back to next tier")
    return []


def _tavily_news(query: str, max_results: int = 6) -> list[dict]:
    """Fetch latest news articles using Tavily topic='news'."""
    return _tavily_search(query, search_depth="basic", max_results=max_results, topic="news")


def _format_tavily(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = []
    # If Tavily synthesized direct answer, put it right at the top
    first_ans = results[0].get("answer") if results else None
    if first_ans:
        lines.append(f"Summary: {first_ans}\n")

    lines.append(f"Search results for: {query}\n")
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   Source: {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _synthesize_with_groq(query: str, context_text: str, mode: str = "research") -> str:
    """Fast synthesis via Groq LPU (300+ tokens/sec) for conversational summaries."""
    from memory.config_manager import get_groq_api_key
    if not get_groq_api_key():
        return context_text

    try:
        from core.llm_client import call_groq_text
        sys_prompt = (
            "You are ZEZO's high-speed real-time web research assistant. "
            "Synthesize the provided web search excerpts into a clear, accurate, 2-3 paragraph answer. "
            "Cite key facts, dates, prices, and sources clearly. Never invent information not present in the snippets."
        )
        user_prompt = f"Topic / Query: {query}\n\nSearch Excerpts:\n{context_text}\n\nSynthesized Intelligence Report:"
        groq_out = call_groq_text(user_prompt, system=sys_prompt, timeout=8, max_tokens=600)
        if groq_out and len(groq_out.strip()) > 30:
            return groq_out.strip()
    except Exception as e:
        _safe_print(f"[WebSearch] ⚠️ Groq synthesis skipped ({e}) — serving raw search text")
    return context_text


def _get_ddgs():
    """
    Returns the DDGS class.  The package was renamed duckduckgo-search -> ddgs;
    the legacy package's endpoints are now rejected by DuckDuckGo (news() gets a
    403 Ratelimit, text() silently returns zero results), so warn loudly if we
    end up on it instead of failing in silence.
    """
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        from duckduckgo_search import DDGS
        print(
            "[WebSearch] ⚠️ Using the deprecated 'duckduckgo-search' package — "
            "DuckDuckGo blocks its endpoints, so every search will come back "
            "empty.  Fix with:  pip install -U ddgs"
        )
        return DDGS


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    DDGS = _get_ddgs()
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
    except Exception as e:
        print(f"[WebSearch] ⚠️ DDG text() failed: {e}")
    return results


def _ddg_news(query: str, max_results: int = 8) -> list[dict]:
    """DDG news search — returns actual articles, not website homepages."""
    DDGS = _get_ddgs()
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("url",    ""),
                    "source":  r.get("source", ""),
                })
    except Exception as e:
        print(f"[WebSearch] ⚠️ DDG news() failed ({e}) — falling back to text search")
    # Also covers the legacy-package case, where news() returns an empty list
    # instead of raising.
    if not results:
        results = _ddg_search(query, max_results=max_results)
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   Source: {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_news(query: str, results: list[dict]) -> str:
    if not results:
        return f"No news found for: {query}"

    lines = [f"Latest news: {query}\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        if not title:
            continue
        src = f"  [{r['source']}]" if r.get("source") else ""
        lines.append(f"{i}. {title}{src}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:140]}")
        if r.get("url"):
            lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Briefing helper ────────────────────────────────────────────────────────────

def _gemini_headlines(n: int = 5) -> tuple[list[str], str]:
    """
    Fetches current headlines via Gemini grounded search.
    Optimised for speed: minimal prompt + strict token cap.
    Returns (headline_list, raw_text_for_display).
    """
    import re
    from core import gemini

    # Fast Tavily News check if key exists
    tav_res = _tavily_news("top world headlines today", max_results=n)
    if tav_res:
        headlines = [r["title"] for r in tav_res if r.get("title")]
        if headlines:
            raw_text = _format_news("top world headlines today", tav_res)
            return headlines[:n], raw_text

    response = gemini.call(
        f"Current world news: {n} headlines. Numbered list, titles only.",
        tier=gemini.SEARCH,
        config={"tools": [{"google_search": {}}]},
        timeout_ms=30_000,
    )
    if response is None:
        return [], ""

    raw = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            raw += part.text

    headlines = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Only accept lines that begin with a number — skips preamble/closing sentences
        if not re.match(r'^[\d]+[.\)\-]', line):
            continue
        clean = re.sub(r'^[\d]+[.\)\-]\s*', '', line)
        clean = re.sub(r'^\*+\s*',          '', clean).strip()
        if clean and len(clean) > 10:
            headlines.append(clean)

    return headlines[:n], raw.strip()


# ── Modes (3-Tier Hierarchy: Tavily AI -> Gemini Grounded -> DuckDuckGo) ──────

def _search(query: str) -> str:
    """Default search: Tier 1 Tavily AI -> Tier 2 Gemini Grounded -> Tier 3 DuckDuckGo."""
    # Tier 1: Tavily AI Search (<500ms)
    tavily_res = _tavily_search(query, search_depth="basic", max_results=6)
    if tavily_res:
        return _format_tavily(query, tavily_res)

    # Tier 2: Gemini Grounded Search
    try:
        return _gemini_search(query)
    except Exception as e:
        _log_gemini_failure("Gemini search", e)

    # Tier 3: DuckDuckGo Fallback
    results = _ddg_search(query)
    return _format_ddg(query, results)


def _news(query: str) -> str:
    """News search: Tier 1 Tavily News -> Tier 2 DDG News -> Tier 3 Gemini."""
    tav_news = _tavily_news(query if query else "world news today", max_results=8)
    if tav_news:
        return _format_news(query if query else "world news today", tav_news)

    ddg_query = query if query else "world news today"
    def _ddg_attempt() -> str:
        return _format_news(ddg_query, _ddg_news(ddg_query, max_results=8))

    text = _run_bounded(_ddg_attempt, timeout=5.0, label="DDG news")
    if text and len(text) > 60 and not text.startswith("No news found"):
        return text

    gemini_query = f"latest news today: {query}" if query else "top world news today"
    text = _run_bounded(
        lambda: _gemini_search(gemini_query), timeout=6.0, label="Gemini news"
    )
    if text and len(text) > 60:
        return text

    return f"No news found for: {query}"


def _research(query: str) -> str:
    """
    Deep dive research mode:
    Tier 1: Tavily Advanced Search + Groq LPU Synthesis (< 700ms total).
    Tier 2: Gemini Grounded Detailed Search.
    Tier 3: DDG Search + Groq / Raw formatting.
    """
    # Tier 1: Tavily Advanced
    tav_res = _tavily_search(query, search_depth="advanced", max_results=8)
    if tav_res:
        formatted = _format_tavily(query, tav_res)
        return _synthesize_with_groq(query, formatted, mode="research")

    # Tier 2: Gemini Grounded
    research_query = (
        f"Comprehensive, detailed explanation of: {query}. "
        "Include background context, key facts, current state, and important nuances."
    )
    try:
        return _gemini_search(research_query)
    except Exception as e:
        _log_gemini_failure("Gemini research", e)

    # Tier 3: DDG Fallback + Groq Synthesis
    results = _ddg_search(query, max_results=10)
    raw_ddg = _format_ddg(query, results)
    return _synthesize_with_groq(query, raw_ddg, mode="research")


def _price(query: str) -> str:
    """Product price lookup: Tier 1 Tavily -> Tier 2 Gemini -> Tier 3 DDG."""
    price_q = f"current price of {query} cost buy today"
    tav_res = _tavily_search(price_q, search_depth="basic", max_results=6)
    if tav_res:
        return _format_tavily(query, tav_res)

    try:
        return _gemini_search(f"current price of {query} — how much does it cost today")
    except Exception as e:
        _log_gemini_failure("Gemini price", e)

    results = _ddg_search(f"{query} price buy", max_results=6)
    return _format_ddg(query, results)


def _compare(items: list[str], aspect: str) -> str:
    """Side-by-side comparison: Tier 1 Tavily + Groq -> Tier 2 Gemini -> Tier 3 DDG."""
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )

    tav_res = _tavily_search(query, search_depth="advanced", max_results=8)
    if tav_res:
        formatted = _format_tavily(query, tav_res)
        return _synthesize_with_groq(query, formatted, mode="compare")

    try:
        return _gemini_search(query)
    except Exception as e:
        _log_gemini_failure("Gemini compare", e)

    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
            if r.get("url"):
                lines.append(f"    {r['url']}")
    raw_comp = "\n".join(lines)
    return _synthesize_with_groq(query, raw_comp, mode="compare")


# ── Public entry point ─────────────────────────────────────────────────────────

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query."

    if items and mode not in ("compare",):
        mode = "compare"

    if player:
        player.write_log(f"[Search:{mode}] {query or ', '.join(items)}")

    _safe_print(f"[WebSearch] 🔍 mode={mode!r}  query={query!r}")

    try:
        if mode == "compare" and items:
            return _compare(items, aspect)
        if mode == "news":
            return _news(query)
        if mode == "research":
            return _research(query)
        if mode == "price":
            return _price(query)
        return _search(query)

    except Exception as e:
        _safe_print(f"[WebSearch] ❌ All backends failed: {e}")
        return f"Search failed: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "web_search",
    "description": "Searches the web. Use for ANY question about current facts, events, prices, or topics — always prefer this over guessing. Never rely on your own memory for current/recent information; your training knowledge is outdated. Search the EXACT product/model/version name the user said — never substitute or 'correct' it with an older name you remember. Modes: 'search' (default), 'news' (latest headlines on a topic), 'research' (deep comprehensive answer), 'price' (product cost lookup), 'compare' (side-by-side comparison of items).",
    "risk": "read_only",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Search query or topic"
            },
            "mode": {
                "type": "STRING",
                "description": "search | news | research | price | compare"
            },
            "items": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "description": "Items to compare (compare mode)"
            },
            "aspect": {
                "type": "STRING",
                "description": "Comparison aspect: price | specs | reviews | features"
            }
        },
        "required": [
            "query"
        ]
    },
    "handler": web_search,
}
