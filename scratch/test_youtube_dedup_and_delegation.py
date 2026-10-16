import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
from core.task_manager import TaskManager, TaskStatus

def test_url_deduplication():
    tm = TaskManager()
    target_url = "https://www.youtube.com/watch?v=xUW_20yku1E"

    def dummy_worker(params, ctx):
        time.sleep(1.0)
        return {"done": True}

    task1 = tm.submit("agent_reach:youtube", dummy_worker, {"target": target_url})
    print(f"Task 1 ID: {task1}")

    # Immediately submit second task with same target
    task2 = tm.submit("agent_reach:youtube", dummy_worker, {"target": target_url})
    print(f"Task 2 ID: {task2}")

    assert task1 == task2, f"Expected task2 ({task2}) to match task1 ({task1}) for identical target URL"
    print("PASS: TaskManager successfully deduplicated identical target URL!")

def test_youtube_video_delegation():
    from actions.youtube_video import youtube_video
    target_url = "https://www.youtube.com/watch?v=xUW_20yku1E"

    # Call youtube_video summarize
    result1 = youtube_video({"action": "summarize", "url": target_url})
    print(f"youtube_video result 1: {result1}")
    assert "Task ID:" in result1, f"Expected asynchronous Task ID in result, got: {result1}"

    # Call youtube_video summarize a second time with the exact same URL
    result2 = youtube_video({"action": "summarize", "url": target_url})
    print(f"youtube_video result 2: {result2}")

    # Extract task IDs from both
    import re
    id1 = re.search(r"Task ID:\s*([a-f0-9]+)", result1).group(1)
    id2 = re.search(r"Task ID:\s*([a-f0-9]+)", result2).group(1)
    assert id1 == id2, f"Expected duplicate call to return same Task ID: {id1} vs {id2}"
    print(f"PASS: Repeated youtube_video call returned identical Task ID ({id1}) without spawning duplicate task!")
    print("PASS: youtube_video successfully delegated to asynchronous background task!")

if __name__ == "__main__":
    test_url_deduplication()
    test_youtube_video_delegation()
    print("ALL RUNTIME TESTS PASSED SUCCESSFULLY!")
