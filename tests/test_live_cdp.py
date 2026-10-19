import subprocess
import time
import urllib.request
import os
import sys

sys.path.insert(0, '.')
from actions.browser_control import _exec_ab

chrome_bin = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
cdp_dir = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\CDP_Profile')
os.makedirs(cdp_dir, exist_ok=True)

flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008
p = subprocess.Popen(
    [chrome_bin, '--remote-debugging-port=9222', '--remote-allow-origins=*', f'--user-data-dir={cdp_dir}', '--no-first-run'],
    creationflags=flags, close_fds=True
)

try:
    # Wait for CDP endpoint
    for _ in range(10):
        try:
            res = urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=1).read().decode()
            if 'webSocketDebuggerUrl' in res:
                break
        except Exception:
            time.sleep(0.5)

    print('=== STEP 1: Navigate to Spotify ===')
    t0 = time.time()
    code, out = _exec_ab('--cdp 9222 open https://open.spotify.com', timeout=15)
    print(f'Navigated in {(time.time() - t0)*1000:.1f}ms: code={code}, out={out}')

    time.sleep(2)

    print('=== STEP 2: Snapshot Homepage ===')
    t0 = time.time()
    code, snap = _exec_ab('--cdp 9222 snapshot -i', timeout=10)
    print(f'Snapshot retrieved in {(time.time() - t0)*1000:.1f}ms, lines={len(snap.splitlines())}')

    login_ref = None
    for line in snap.splitlines():
        if 'button "Log in"' in line:
            import re
            m = re.search(r'\[ref=([^\]]+)\]', line)
            if m:
                login_ref = f'@{m.group(1)}'
                print(f'Found Log in ref: {login_ref} -> {line.strip()}')
                break

    if not login_ref:
        print('Could not find Log in button ref in snapshot!')
        print('First 20 lines of snapshot:')
        for l in snap.splitlines()[:20]:
            print('  ', l)
    else:
        print(f'=== STEP 3: Click Log In ({login_ref}) ===')
        t0 = time.time()
        code, out = _exec_ab(f'--cdp 9222 click {login_ref}', timeout=10)
        print(f'Clicked in {(time.time() - t0)*1000:.1f}ms: code={code}, out={out}')

        time.sleep(3)

        print('=== STEP 4: Inspect Accounts/Login Page ===')
        code_url, current_url = _exec_ab('--cdp 9222 get url', timeout=10)
        print('Current URL:', current_url)

        t0 = time.time()
        code, login_snap = _exec_ab('--cdp 9222 snapshot -i', timeout=10)
        print(f'Login page snapshot retrieved in {(time.time() - t0)*1000:.1f}ms, lines={len(login_snap.splitlines())}')

        google_ref = None
        for line in login_snap.splitlines():
            if 'google' in line.lower():
                print('   Google element found:', line.strip())
                import re
                m = re.search(r'\[ref=([^\]]+)\]', line)
                if m and not google_ref:
                    google_ref = f'@{m.group(1)}'

        if google_ref:
            print(f'=== STEP 5: Click Google Login Button ({google_ref}) ===')
            t0 = time.time()
            code, out = _exec_ab(f'--cdp 9222 click {google_ref}', timeout=10)
            print(f'Clicked Google button in {(time.time() - t0)*1000:.1f}ms: code={code}, out={out}')

            time.sleep(3)
            code_url, final_url = _exec_ab('--cdp 9222 get url', timeout=10)
            print('URL after Google click:', final_url)
        else:
            print('Could not find Google button in login snapshot!')

finally:
    p.terminate()
    print('Chrome terminated.')
