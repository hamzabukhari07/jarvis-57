"""
Quick Verification Script for ZEZO Browser Control (agent-browser Rust CDP)
"""
from actions.browser_control import browser_control

def main():
    print("1. Opening Example.com...")
    print(browser_control({"action": "go_to", "url": "https://example.com"}))

    print("\n2. Getting Ref-based Interactive Snapshot...")
    print(browser_control({"action": "snapshot"}))

    print("\n3. Clicking element @e1...")
    print(browser_control({"action": "click", "selector": "@e1"}))

    print("\n4. Getting Current URL...")
    print(browser_control({"action": "get_url"}))

    print("\n5. Closing browser session...")
    print(browser_control({"action": "close"}))

if __name__ == "__main__":
    main()
