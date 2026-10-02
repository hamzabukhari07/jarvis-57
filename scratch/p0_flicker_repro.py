"""P0 flicker reproduction — frontend activity stream/log rendering.

Root cause: appending log cards with `box.innerHTML += html` serializes the
ENTIRE container back to a string, then re-parses it. Every existing
`.stream-msg` child is destroyed and recreated on every new line. That churn
is what makes the panel blink (nodes repainted, <iconify-icon> re-resolved,
CSS entrance animation restarted).

`insertAdjacentHTML('beforeend', html)` parses only the new fragment and
leaves existing nodes untouched.

Metric: MutationObserver childList added/removed nodes (deterministic).

Run: python scratch/p0_flicker_repro.py
Exit 0 = root cause confirmed.
"""
import sys
from playwright.sync_api import sync_playwright

N = 10
# innerHTML += : append k only inserts k nodes but destroys all previous ones.
EXPECTED_BAD_ADDED = N * (N + 1) // 2          # 1+2+...+N = 55
EXPECTED_BAD_REMOVED = N * (N - 1) // 2        # 0+1+...+(N-1) = 45
EXPECTED_GOOD_ADDED = N                        # 10
EXPECTED_GOOD_REMOVED = 0

HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
  @keyframes msgFadeIn { from { opacity: 0; transform: translateY(4px);} to { opacity:1; transform: translateY(0);} }
  .stream-msg { animation: msgFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1); padding: 4px; }
</style></head><body></body></html>
"""

JS = """
async ([n]) => {
  window.__r = { bad: 0, good: 0, badChildren: 0, goodChildren: 0,
                 badFirstChanges: 0, goodFirstChanges: 0 };
  const frame = () => new Promise(r => setTimeout(r, 20));

  async function run(kind) {
    const box = document.createElement('div');
    document.body.appendChild(box);
    const obs = new MutationObserver((records) => {
      for (const rec of records) {
        window.__r[kind] += rec.addedNodes.length;
      }
    });
    obs.observe(box, { childList: true });
    let prevFirst = null;
    for (let i = 0; i < n; i++) {
      const html = '<div class="stream-msg">msg ' + i + '</div>';
      if (kind === 'bad') { box.innerHTML += html; }             // current code
      else { box.insertAdjacentHTML('beforeend', html); }        // proposed fix
      if (prevFirst && box.firstElementChild !== prevFirst) window.__r[kind + 'FirstChanges']++;
      prevFirst = box.firstElementChild;
      await frame();
    }
    obs.takeRecords();
    obs.disconnect();
    window.__r[kind + 'Children'] = box.children.length;
  }

  await run('bad');
  await run('good');
  return window.__r;
}
"""


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML)
        result = page.evaluate(JS, [N])
        browser.close()

    bad_added = result["bad"]
    good_added = result["good"]
    print(f"appends per container          : {N}")
    print(f"innerHTML +=  nodes added      : {bad_added}  (expected {EXPECTED_BAD_ADDED})")
    print(f"innerHTML +=  first-child swaps: {result['badFirstChanges']}")
    print(f"insertAdjacentHTML nodes added : {good_added}  (expected {EXPECTED_GOOD_ADDED})")
    print(f"insertAdjacentHTML 1st swaps   : {result['goodFirstChanges']}")
    print(f"children kept bad / good       : {result['badChildren']} / {result['goodChildren']}")

    ok = (
        bad_added == EXPECTED_BAD_ADDED
        and good_added == EXPECTED_GOOD_ADDED
        and result["goodFirstChanges"] == 0
        and result["badFirstChanges"] >= N - 2
        and result["badChildren"] == N
        and result["goodChildren"] == N
    )
    print("ROOT CAUSE CONFIRMED" if ok else "REPRO DID NOT MATCH EXPECTATION")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
