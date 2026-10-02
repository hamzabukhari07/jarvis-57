import sys
import os

sys.path.insert(0, os.path.abspath("."))
from actions.computer_control import computer_control, TOOL

def test_batch_action():
    assert "batch" in TOOL["parameters"]["properties"]["action"]["description"]
    assert "sequence" in TOOL["parameters"]["properties"]
    
    # Test batch execution with mock / safe actions
    params = {
        "action": "batch",
        "sequence": [
            {"action": "random_data", "type": "name"},
            {"action": "wait", "seconds": 0.05},
            {"action": "random_data", "type": "email"},
        ]
    }
    
    res = computer_control(params)
    print(f"Batch execution result:\n{res}")
    assert "Executed 3 batch steps successfully" in res
    assert "random_data" in res
    print("\n[PASS] Batch Macro Action Test Passed Successfully!")

if __name__ == "__main__":
    test_batch_action()
