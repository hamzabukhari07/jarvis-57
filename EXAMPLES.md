# Examples

Real-world code examples demonstrating the four principles. Each example shows what LLMs commonly do wrong and how to fix it.

---

## 1. Think Before Coding

### Example 1: Hidden Assumptions

**User Request:** "Add a feature to export user data"

**❌ What LLMs Do (Wrong Assumptions)**

```python
def export_users(format='json'):
    """Export all users to a file."""
    users = User.query.all()
    
    if format == 'json':
        with open('users.json', 'w') as f:
            json.dump([u.to_dict() for u in users], f)
    elif format == 'csv':
        with open('users.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'email', 'name'])
            writer.writeheader()
            writer.writerows([u.to_dict() for u in users])
    
    return f"Exported {len(users)} users"
```

**Problems:**
- Assumed it should export ALL users (what about pagination? privacy?)
- Assumed file location without asking
- Assumed which fields to include
- Assumed CSV fieldnames without checking actual data structure

**✅ What Should Happen (Surface Assumptions)**

```
Before implementing, I need to clarify:

1. **Scope**: Export all users or filtered subset? (privacy implications)
2. **Format**: You mentioned "export" - did you mean:
   - Download file in browser?
   - Background job with email notification?
   - API endpoint returning data?
3. **Fields**: Which user fields? (some might be sensitive)
4. **Volume**: How many users typically? (affects approach)

Simplest approach: Add an API endpoint that returns paginated JSON.
Would need more info for file-based exports.

What's your preference?
```

### Example 2: Multiple Interpretations

**User Request:** "Make the search faster"

**❌ What LLMs Do (Pick Silently)**

```python
# Adds caching, database indexes, and async processing
# without asking which "faster" matters
@lru_cache(maxsize=1000)
async def search(query: str) -> List[Result]:
    # ... 200 lines of optimization code
```

**✅ What Should Happen**

```
"Make the search faster" could mean:

1. **Faster response time** (< 100ms instead of 500ms)
   - Add database indexes
   - Cache frequent queries
   - Estimated effort: 2 hours

2. **Handle more concurrent searches** (throughput)
   - Add async/await
   - Connection pooling
   - Estimated effort: 4 hours

3. **Faster perceived speed** (UX)
   - Show partial results immediately
   - Progressive loading
   - Estimated effort: 3 hours

Current search takes ~500ms for typical queries. 
Which aspect matters most for your use case?
```

---

## 2. Simplicity First

### Example 1: Over-abstraction

**User Request:** "Add a function to calculate discount"

**❌ What LLMs Do (Overengineered)**

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol, Union
from dataclasses import dataclass

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float:
        pass

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percentage: float):
        self.percentage = percentage
    
    def calculate(self, amount: float) -> float:
        return amount * (self.percentage / 100)

class FixedDiscount(DiscountStrategy):
    def __init__(self, fixed_amount: float):
        self.fixed_amount = fixed_amount
    
    def calculate(self, amount: float) -> float:
        return min(self.fixed_amount, amount)

@dataclass
class DiscountConfig:
    strategy: DiscountStrategy
    min_purchase: float = 0.0
    max_discount: float = float('inf')

class DiscountCalculator:
    def __init__(self, config: DiscountConfig):
        self.config = config
    
    def apply_discount(self, amount: float) -> float:
        if amount < self.config.min_purchase:
            return 0
        discount = self.config.strategy.calculate(amount)
        return min(discount, self.config.max_discount)

# Usage requires 30+ lines of setup for a simple calculation
```

**✅ What Should Happen (Simple)**

```python
def calculate_discount(amount: float, percent: float) -> float:
    """Calculate discount amount. percent should be 0-100."""
    return amount * (percent / 100)

# Usage
discount = calculate_discount(100.0, 10.0)  # $10 off
```

**When to add complexity:** Only when you actually need multiple discount types. If that requirement comes later, refactor then.

### Example 2: Speculative Features

**User Request:** "Save user preferences to database"

**❌ What LLMs Do (Unnecessary Features)**

```python
class PreferenceManager:
    def __init__(self, db, cache=None, validator=None):
        self.db = db
        self.cache = cache or InMemoryCache()
        self.validator = validator or DefaultValidator()
    
    def save(self, user_id: int, prefs: dict, 
             merge: bool = True, 
             validate: bool = True,
             notify: bool = False) -> bool:
        """Save preferences with optional merging, validation, and notifications."""
        
        if validate:
            errors = self.validator.validate(prefs)
            if errors:
                raise ValidationError(errors)
        
        existing = self.get(user_id) if merge else {}
        
        if merge:
            existing.update(prefs)
            prefs = existing
        
        self.db.execute(
            "UPDATE users SET preferences = ? WHERE id = ?",
            (json.dumps(prefs), user_id)
        )
        
        if self.cache:
            self.cache.set(f"prefs:{user_id}", prefs)
        
        if notify:
            self.notify_preference_change(user_id, prefs)
        
        return True
    
    def notify_preference_change(self, user_id: int, prefs: dict):
        # Another 30 lines for a feature nobody asked for
        pass
```

**✅ What Should Happen (Just What Was Asked)**

```python
def save_preferences(db, user_id: int, preferences: dict):
    """Save user preferences to database."""
    db.execute(
        "UPDATE users SET preferences = ? WHERE id = ?",
        (json.dumps(preferences), user_id)
    )
```

**Add later if needed:** Caching (when performance matters), validation (when bad data appears), merging (when requirement emerges).

---

## 3. Surgical Changes

### Example 1: Drive-by Refactoring

**User Request:** "Fix the bug where empty emails crash the validator"

**❌ What LLMs Do (Too Much)**

```diff
  def validate_user(user_data):
-     # Check email format
-     if not user_data.get('email'):
+     """Validate user data."""
+     email = user_data.get('email', '').strip()
+     
+     # Validate email
+     if not email:
          raise ValueError("Email required")
-     
-     # Basic email validation
-     if '@' not in user_data['email']:
+     if '@' not in email or '.' not in email.split('@')[1]:
          raise ValueError("Invalid email")
      
-     # Check username
-     if not user_data.get('username'):
+     # Validate username
+     username = user_data.get('username', '').strip()
+     if not username:
          raise ValueError("Username required")
+     if len(username) < 3:
+         raise ValueError("Username too short")
+     if not username.isalnum():
+         raise ValueError("Username must be alphanumeric")
      
      return True
```

**Problems:**
- "Improved" email validation beyond the bug fix
- Added username validation nobody asked for
- Changed comments
- Added docstring

**✅ What Should Happen (Surgical)**

```diff
  def validate_user(user_data):
      # Check email format
-     if not user_data.get('email'):
+     email = user_data.get('email', '')
+     if not email or not email.strip():
          raise ValueError("Email required")
      
      # Basic email validation
-     if '@' not in user_data['email']:
+     if '@' not in email:
          raise ValueError("Invalid email")
      
      # Check username
      if not user_data.get('username'):
          raise ValueError("Username required")
      
      return True
```

**Only changed:** The specific lines that fix empty email handling.

### Example 2: Style Drift

**User Request:** "Add logging to the upload function"

**❌ What LLMs Do (Reformat Everything)**

```diff
- def upload_file(file_path, destination):
+ def upload_file(file_path: str, destination: str) -> bool:
+     """Upload file to destination with logging."""
+     logger.info(f"Uploading {file_path} to {destination}")
+     
      try:
-         with open(file_path, 'rb') as f:
-             data = f.read()
-         
-         response = requests.post(destination, files={'file': data})
-         
-         if response.status_code == 200:
-             return True
-         else:
-             return False
+         with open(file_path, "rb") as f:
+             data = f.read()
+         response = requests.post(destination, files={"file": data})
+         success = response.status_code == 200
+         
+         if success:
+             logger.info(f"Upload successful: {file_path}")
+         else:
+             logger.error(f"Upload failed: {file_path}, status={response.status_code}")
+         
+         return success
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f"Upload error for {file_path}: {e}")
          return False
```

**Problems:**
- Changed quote style ('' to "")
- Added type hints nobody asked for
- Added docstring
- Reformatted whitespace
- Changed boolean return logic

**✅ What Should Happen (Match Existing Style)**

```diff
+ import logging
+ 
+ logger = logging.getLogger(__name__)
+ 
  def upload_file(file_path, destination):
+     logger.info(f'Starting upload: {file_path}')
      try:
          with open(file_path, 'rb') as f:
              data = f.read()
          
          response = requests.post(destination, files={'file': data})
          
          if response.status_code == 200:
+             logger.info(f'Upload successful: {file_path}')
              return True
          else:
+             logger.error(f'Upload failed: {file_path}, status={response.status_code}')
              return False
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f'Upload error: {file_path}')
          return False
```

**Matched:** Single quotes, no type hints, existing boolean pattern, spacing style.

---

## 4. Goal-Driven Execution

### Example 1: Vague vs. Verifiable

**User Request:** "Fix the authentication system"

**❌ What LLMs Do (Vague Approach)**

```
I'll fix the authentication system by:
1. Reviewing the code
2. Identifying issues
3. Making improvements
4. Testing the changes

[Proceeds to make changes without clear success criteria]
```

**✅ What Should Happen (Verifiable Goals)**

```
To "fix authentication," I need to define success criteria. 
What specific issue are we solving?

If the issue is "users stay logged in after password change":

Plan:
1. Write test: Change password → verify old session invalidated
   Verify: Test fails (reproduces bug)

2. Implement: Invalidate sessions on password change
   Verify: Test passes

3. Check edge cases: Multiple active sessions, concurrent changes
   Verify: Additional tests pass

4. Verify no regression: Existing auth tests still pass
   Verify: Full test suite green

Current test coverage for auth: [shows coverage]
What's the specific auth issue you're seeing?
```

### Example 2: Multi-Step with Verification

**User Request:** "Add rate limiting to the API"

**❌ What LLMs Do (All at Once)**

```python
# Implements full rate limiting with Redis, multiple strategies,
# configuration system, and monitoring in one 300-line commit
# No clear verification steps
```

**✅ What Should Happen (Incremental with Verification)**

```
Plan for rate limiting:

1. Add basic in-memory rate limiting (single endpoint)
   Verify: 
   - Test: 100 requests → first 10 succeed, rest get 429
   - Manual: curl endpoint 11 times, see rate limit error

2. Extract to middleware (apply to all endpoints)
   Verify:
   - Test: Rate limits apply to /users and /posts
   - Existing endpoint tests still pass

3. Add Redis backend (for multi-server)
   Verify:
   - Test: Rate limit persists across app restarts
   - Test: Two app instances share rate limit counter

4. Add configuration (rates per endpoint)
   Verify:
   - Test: /search allows 10/min, /users allows 100/min
   - Config file parsed correctly

Each step is independently verifiable and deployable.
Start with step 1?
```

### Example 3: Test-First Verification

**User Request:** "The sorting breaks when there are duplicate scores"

**❌ What LLMs Do (Fix Without Reproducing)**

```python
# Immediately changes sort logic without confirming the bug
def sort_scores(scores):
    return sorted(scores, key=lambda x: (-x['score'], x['name']))
```

**✅ What Should Happen (Reproduce First)**

```python
# 1. First, write a test that reproduces the issue
def test_sort_with_duplicate_scores():
    """Test sorting when multiple items have same score."""
    scores = [
        {'name': 'Alice', 'score': 100},
        {'name': 'Bob', 'score': 100},
        {'name': 'Charlie', 'score': 90},
    ]
    
    result = sort_scores(scores)
    
    # The bug: order is non-deterministic for duplicates
    # Run this test multiple times, it should be consistent
    assert result[0]['score'] == 100
    assert result[1]['score'] == 100
    assert result[2]['score'] == 90

# Verify: Run test 10 times → fails with inconsistent ordering

# 2. Now fix with stable sort
def sort_scores(scores):
    """Sort by score descending, then name ascending for ties."""
    return sorted(scores, key=lambda x: (-x['score'], x['name']))

# Verify: Test passes consistently
```

---

## Anti-Patterns Summary

| Principle | Anti-Pattern | Fix |
|-----------|-------------|-----|
| Think Before Coding | Silently assumes file format, fields, scope | List assumptions explicitly, ask for clarification |
| Simplicity First | Strategy pattern for single discount calculation | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds type hints while fixing bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |

## Key Insight

The "overcomplicated" examples aren't obviously wrong—they follow design patterns and best practices. The problem is **timing**: they add complexity before it's needed, which:

- Makes code harder to understand
- Introduces more bugs
- Takes longer to implement
- Harder to test

The "simple" versions are:
- Easier to understand
- Faster to implement
- Easier to test
- Can be refactored later when complexity is actually needed

**Good code is code that solves today's problem simply, not tomorrow's problem prematurely.**

---

## 5. ZEZO-Specific Golden Patterns & Idioms

### Example 1: Creating or Updating an Action Tool (`actions/*.py`)

**User Request:** "Add a new tool `actions/system_battery.py` to check battery percentage and power status"

**❌ What LLMs Do (Missing Risk, Schema Drift, Blocking Calls)**

```python
import subprocess

# Missing Gemini TOOL declaration or missing mandatory 'risk' field!
TOOL = {
    "name": "system_battery",
    "description": "Get battery status"
    # Missing 'risk' -> core/action_loader.py will REJECT this tool!
}

def handler(parameters: dict, **kwargs):
    # Pops up terminal window on Windows and blocks the UI thread!
    res = subprocess.check_output("WMIC Path Win32_Battery Get EstimatedChargeRemaining")
    return res.decode()
```

**✅ What Should Happen (Complete ZEZO Action Pattern)**

```python
"""
actions/system_battery.py — Query system battery and power telemetry.
Follows ZEZO action tool standards: Gemini schema, risk tier, non-blocking execution.
"""
import os
import sys
import asyncio
import subprocess

TOOL = {
    "name": "system_battery",
    "description": "Check device battery percentage, charging state, and power profile.",
    "risk": "read_only",  # MANDATORY: 'read_only' | 'low' | 'medium' | 'high' | 'critical'
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "detailed": {
                "type": "BOOLEAN",
                "description": "Whether to return full hardware telemetry including wear level."
            }
        },
        "required": []
    }
}

async def _fetch_battery_async() -> dict:
    """Run non-blocking subprocess with hidden terminal window."""
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance -ClassName Win32_Battery | Select-Object -Property EstimatedChargeRemaining, BatteryStatus"]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=creationflags
    )
    stdout, stderr = await proc.communicate()
    # Parse and return structured payload
    return {"percent": 85, "charging": True, "raw": stdout.decode("utf-8", errors="ignore").strip()}

def handler(parameters: dict, **kwargs) -> dict:
    """Action entry point. Always returns a structured dict."""
    try:
        # Run async worker cleanly in current or new event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _fetch_battery_async()).result(timeout=5)
        else:
            result = asyncio.run(_fetch_battery_async())
            
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Synchronized Docs & Journal Step (Mandatory):**
- Update `docs/TOOLS.md` with the new tool name, parameters, and risk level.
- Append an entry in `LEARNING_JOURNAL.md`.

---

### Example 2: The Audio & Voice Pipeline Hands-Off Guard

**User Request:** "Fix the issue where website cloner does not open `rebuilt.html` in the user's browser"

**❌ What LLMs Do (Violating Rule 6 / Hands-Off Policy)**
- Modifies `main.py` live audio loops (`_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`)
- Refactors `core/audio_devices.py` or adjusts sample rates
- Touches 5 unrelated files across audio and UI

**✅ What Should Happen (Surgical Fix with Strict Hands-Off)**
- **Recognize Rule 6:** Audio pipeline is 100% off-limits.
- **Inspect `actions/website_cloner.py` directly.**
- Spot that `browser_control` rejects `file://` URIs and replace it with `webbrowser.open(target_url)` or `os.startfile(file_path)` on Windows.
- **Touched files:** ONLY `actions/website_cloner.py` (and corresponding `docs/WEBSITE_CLONER.md` if behavior changed).

---

### Example 3: Frontend ReUI Design System Pattern

**User Request:** "Add a refresh button to the Code Engines settings tab"

**❌ What LLMs Do (Raw HTML & Hardcoded Hex Colors)**

```tsx
// ❌ Violates ReUI rule & hardcodes styling
<button 
  style={{ background: "#3b82f6", color: "#fff", padding: "8px 16px", borderRadius: "4px" }}
  onClick={handleRefresh}
>
  Refresh Engines
</button>
```

**✅ What Should Happen (Use Official ReUI Component & Semantic Tokens)**

```tsx
// ✅ Uses ReUI Button, Lucide icons, and semantic CSS variables
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"

<Button 
  variant="outline" 
  size="sm" 
  onClick={handleRefresh}
  disabled={isLoading}
  className="gap-2 text-foreground hover:bg-accent"
>
  <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
  Refresh Engines
</Button>
```

---

### Example 4: Pre-Flight Docs Reading & Post-Flight Docs Sync

**User Request:** "Add a new specialized agent 'Scout' to the fleet management system"

**❌ What LLMs Do (Guessing Architecture & Leaving Docs Stale)**
- Hardcodes the agent in a random dictionary in `main.py`.
- Doesn't read `docs/FLEET_MANAGEMENT.md` to see that Scranton Office uses `OFFICE_DESK_COORDINATES` in `core/fleet_manager.py` and React coordinates in `AutonomousOfficeScreen.tsx`.
- Completes the code but leaves `docs/FLEET_MANAGEMENT.md` outdated.

**✅ What Should Happen**
1. **Pre-Flight (Rule 1):** Read `docs/FLEET_MANAGEMENT.md` to understand desk coordinates, risk tiers (`L0_READ_ONLY`, `L1_MUTATION`, `L2_DESTRUCTIVE`), and role dispatch keywords.
2. **Execute (Rule 3 & 4):** Add 'Scout' with assigned desk coordinates in `core/fleet_manager.py` and update `AutonomousOfficeScreen.tsx`.
3. **Post-Flight Sync (Rule 10):**
   - Update `docs/FLEET_MANAGEMENT.md` with Scout's role, coordinates, and skills.
   - Append entry to `LEARNING_JOURNAL.md`.
4. **Verify (Rule 7):** Check syntax (`python -m py_compile`), test desk rendering, and confirm existing agents are unaffected.

---

### Example 5: Error Handling & TaskGroup Protection (Never Crash Live Sessions)

**User Request:** "Fetch active Wi-Fi networks in a new helper tool"

**❌ What LLMs Do (Raising Unhandled Exceptions & Crashing Gemini Live)**

```python
def handler(parameters: dict, **kwargs):
    # If netsh fails or wifi is turned off, this raises CalledProcessError!
    # In an asyncio.TaskGroup, an unhandled exception cancels ALL concurrent tasks
    # and tears down the entire Gemini Live voice session!
    output = subprocess.check_output(["netsh", "wlan", "show", "networks"]).decode()
    return {"networks": output.splitlines()}
```

**✅ What Should Happen (Graceful Degradation & Structured Errors)**

```python
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)

def handler(parameters: dict, **kwargs) -> dict:
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            ["netsh", "wlan", "show", "networks"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=creationflags
        )
        if proc.returncode != 0:
            logger.warning(f"Wi-Fi query returned non-zero code: {proc.stderr}")
            return {
                "status": "warning",
                "message": "Wi-Fi adapter may be disabled or disconnected.",
                "networks": []
            }
        
        # Parse output safely
        networks = [line.strip() for line in proc.stdout.splitlines() if "SSID" in line]
        return {"status": "success", "networks": networks}

    except subprocess.TimeoutExpired:
        logger.error("Wi-Fi scan command timed out after 5s")
        return {"status": "error", "message": "Wi-Fi hardware query timed out."}
    except Exception as e:
        logger.exception(f"Unexpected error querying Wi-Fi networks: {e}")
        return {"status": "error", "message": f"Hardware error: {str(e)}"}
```

---

### Example 6: 3-Tier Escalated Perception (Fast UIA vs Heavy Vision)

**User Request:** "Click the 'Export' button in the active desktop app"

**❌ What LLMs Do (Premature Escalation to Heavy Vision)**

```python
# ❌ Takes a screenshot and sends it to Gemini Vision immediately!
# Latency: ~2.5 seconds, high token cost, prone to bounding box inaccuracies.
screenshot = take_screenshot()
coords = gemini_vision_find_element(screenshot, "Export button")
click(coords)
```

**✅ What Should Happen (Tier 1 UIA -> Tier 1.5 OCR -> Tier 2 Vision)**

```python
# ✅ Follows ZEZO's 3-Tier Escalation:
# Tier 1: Windows UIA COM Worker (<15ms, 0 API tokens)
element = uia_find_element_by_name(window_handle, "Export")
if element:
    element.click()
    return {"status": "success", "method": "uia"}

# Tier 1.5: Multilingual RapidOCR (<80ms, CPU ONNX, 0 VRAM)
ocr_boxes = local_rapid_ocr_scan(screenshot)
box = match_ocr_text(ocr_boxes, "Export")
if box:
    click_center(box)
    return {"status": "success", "method": "rapid_ocr"}

# Tier 2: Gemini Vision (~2s fallback ONLY when accessibility and text are absent)
return fallback_gemini_vision_locate_and_click(screenshot, "Export button")
```

---

### Example 7: Windows Subprocess & Terminal Window Isolation

**User Request:** "Run a git status check inside an action handler"

**❌ What LLMs Do (Spawning Black Terminal Windows & shell=True)**

```python
# ❌ shell=True security risk + missing CREATE_NO_WINDOW
# Pops up a black command prompt window on the user's screen during voice interaction!
res = subprocess.check_output(f"git status {path}", shell=True)
```

**✅ What Should Happen (Argument List, Timeout & CREATE_NO_WINDOW)**

```python
import sys
import subprocess

creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
try:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path,
        capture_output=True,
        text=True,
        timeout=5,
        creationflags=creationflags  # Guaranteed hidden on Windows
    )
    output = res.stdout.strip()
except subprocess.TimeoutExpired:
    output = ""
```

---

### Example 8: ReUI Modal Invariants & Window Animation Economy

**User Request:** "Create a new modal component for viewing task logs"

**❌ What LLMs Do (Backdrop-filters Inside Modals & Unbounded CSS Transitions)**

```css
/* ❌ Inside modal panel: causes GPU rendering artifacts and blur bugs */
.modal-content {
  backdrop-filter: blur(12px); /* FORBIDDEN inside modals */
  background: rgba(0, 0, 0, 0.4); /* Panel must be opaque #0a0a0a */
  transition: all 0.3s ease; /* FORBIDDEN: never use transition: all */
}
```

**✅ What Should Happen (Opaque Panel, Explicit Transitions & Anim State)**

```tsx
// ✅ Invariant: .modal-overlay has blur, modal card is opaque #0a0a0a
// Invariant: explicit transitions only
// Invariant: manage window._zezoAnimActive to freeze background 3D canvas/vortex while modal is open

export function TaskLogsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  useEffect(() => {
    if (isOpen) {
      window._zezoAnimActive = false; // Pause background 3D WebGL / Vortex loop
    } else {
      window._zezoAnimActive = true;
    }
    return () => { window._zezoAnimActive = true; };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
      <div className="w-full max-w-2xl bg-[#0a0a0a] border border-border rounded-xl p-6 shadow-2xl transition-[opacity,transform] duration-200">
        {/* Modal content */}
      </div>
    </div>
  );
}
```