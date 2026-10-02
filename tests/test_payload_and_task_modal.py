import json
from pathlib import Path
import pytest
from core.repo_context import remember_repo, get_last_repo, forget_repo

def test_repo_forget_and_remember(tmp_path):
    fake_repo = tmp_path / "test_project"
    fake_repo.mkdir()
    
    remember_repo(str(fake_repo))
    assert get_last_repo() == str(fake_repo.resolve())
    
    forget_repo(str(fake_repo))
    assert get_last_repo() is None

def test_frontend_payload_and_modal_elements():
    html_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    
    # Check that FULL LOG button is removed from task modal and COPY LOGS is present
    assert "btn-copy-task-logs" in content
    assert "copyTaskLogsFromDetail" in content
    assert "viewTaskInFullLog" not in content
    
    # Check that payload dropzone is clean (no unnecessary list of formats)
    assert "PDF, DOCX, CSV, PNG, TXT, PY or Website Folder" not in content
    
def test_file_controller_find_files(tmp_path):
    from actions.file_controller import find_files, file_controller
    
    # Create test file
    test_file = tmp_path / "Rust_vs_Go_Report.md"
    test_file.write_text("# Test", encoding="utf-8")
    
    res = find_files(name="Rust_vs_Go_Report.md", path=str(tmp_path))
    assert "Rust_vs_Go_Report.md" in res
    assert "Search error" not in res
    
    # Test via action handler
    handler_res = file_controller({"action": "find", "name": "Rust_vs_Go_Report.md", "path": str(tmp_path)})
    assert "Rust_vs_Go_Report.md" in handler_res
    assert "Search error" not in handler_res

def test_agent_reach_instagram_schema_and_extraction():
    from actions.agent_reach import TOOL, agent_reach_action, fetch_instagram_content
    
    assert "instagram" in TOOL["parameters"]["properties"]["platform"]["enum"]
    assert "tiktok" in TOOL["parameters"]["properties"]["platform"]["enum"]
    
    # Test action handler dispatching with mismatched platform='youtube'
    url = "https://www.instagram.com/reel/DYhQS_zhqZ6/?stkn=MTBzMTEzdHF4OXJocw=="
    res = agent_reach_action({"target": url, "platform": "youtube"})
    assert "instagram" in res.lower()
    assert "Task ID" in res or "Instagram" in res
    
    # Test real extraction function with the exact URL
    content = fetch_instagram_content(url)
    assert "Instagram" in content
    assert "nuthan" in content or "OpenSpec" in content or "Creator" in content
    # Audio transcript extracted
    assert "Spoken Audio Transcript" in content or "Caption" in content

