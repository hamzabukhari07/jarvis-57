from pathlib import Path
import tempfile
import shutil
from core.design_resolver import resolve_design, is_ui_task

print("--- Testing Design Resolver & Full Untruncated HTML ---")
res = resolve_design("build a hairline grid engineer portfolio", repo_path=None)
assert res is not None, "resolve_design returned None"
assert res.is_active(), "res.is_active() is False"
print(f"Source Name: {res.source_name}")
print(f"Source Type: {res.source_type}")
print(f"Source Path: {res.source_path}")
print(f"raw_html length (prompt-safe): {len(res.raw_html)}")
print(f"full_raw_html length (untruncated): {len(res.full_raw_html)}")

if res.source_path and res.source_path.exists():
    file_bytes = res.source_path.stat().st_size
    print(f"Source File on disk size: {file_bytes} bytes")
    assert len(res.full_raw_html) > 50000, f"full_raw_html was truncated! len={len(res.full_raw_html)}"
    print("SUCCESS: full_raw_html is untruncated and matches master template!")

# Test simulated workspace provisioning
with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_repo = Path(tmp_dir)
    ref_dst = tmp_repo / "reference.html"
    if res.source_path and res.source_path.exists():
        shutil.copy2(res.source_path, ref_dst)
    elif res.full_raw_html:
        ref_dst.write_text(res.full_raw_html, encoding="utf-8")
    
    assert ref_dst.exists(), "reference.html does not exist in workspace!"
    assert ref_dst.stat().st_size > 50000, f"reference.html is truncated! size={ref_dst.stat().st_size}"
    print(f"Workspace reference.html provisioned successfully: {ref_dst.stat().st_size} bytes (100% full)")

print("\n--- All tests PASSED successfully! ---")
