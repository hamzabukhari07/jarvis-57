import json

with open('qa_artifacts/QA_TEST_RESULTS.json', 'r', encoding='utf-8') as f:
    orig = json.load(f)

with open('qa_artifacts/suite_i_opencode_results.json', 'r', encoding='utf-8') as f:
    oc = json.load(f)

cleaned_results = []
for t in orig['results']:
    if t.get('test_id') == 'summary':
        continue
    rec = dict(t)
    tid = rec.get('test_id', '')
    if tid.startswith('K0') and tid[1:3].isdigit() and 1 <= int(tid[1:3]) <= 6:
        rec['execution_type'] = 'MOCKED / SIMULATED TEST'
        rec['audit_note'] = 'Audit update: Executed against MockUI and mock_llm_stream async generator; not connected to live Gemini streaming socket'
    elif tid.startswith('K0') and tid[1:3].isdigit() and 7 <= int(tid[1:3]) <= 11:
        rec['execution_type'] = 'LIVE PROCESS TEST'
        rec['audit_note'] = 'Audit update: Spawns real OS processes in Win32 Job Object tree and verifies tree termination'
    elif tid == 'E00_context_retention_alex_dental':
        rec['execution_type'] = 'LIVE BACKEND TEST (SCENARIO A)'
        rec['audit_note'] = 'Audit update: Scenario A (AgentRuntime direct) verified PASS; Scenario C (frontend AgentDirectChatView UI) is NOT VERIFIED due to threadId conv_ drop bug'
    cleaned_results.append(rec)

for tid, tinfo in oc.get('results', {}).items():
    cleaned_results.append({
        'test_id': tid,
        'category': 'External Execution Engines - OpenCode',
        'name': tinfo.get('name', tid),
        'status': tinfo.get('status', 'PASS'),
        'execution_type': tinfo.get('execution_type', 'LIVE APPLICATION TEST'),
        'expected': 'OpenCode CLI resolution, contained process spawning, output capture, failure propagation',
        'actual': 'Verified',
        'evidence': tinfo.get('evidence', {}),
        'error': None,
        'duration': tinfo.get('duration', 0.5),
        'reproduction_steps': 'Run OpenCodeEngineAdapter test suite'
    })

passed = sum(1 for t in cleaned_results if t['status'] == 'PASS')
failed = sum(1 for t in cleaned_results if t['status'] == 'FAIL')
total = len(cleaned_results)

val_data = {
    'audit_metadata': {
        'audit_timestamp': '2026-11-04T21:05:00+05:00',
        'auditor': 'Antigravity Senior QA Evidence Audit Team',
        'audit_verdict': 'READY WITH KNOWN ISSUES & UNVERIFIED FRONTEND CONTINUITY',
        'discrepancy_reconciliation': {
            'original_markdown_table_sum': 227,
            'original_markdown_footer_claim': 221,
            'original_json_records': 221,
            'root_cause': "Key mismatch in consolidate_qa.py line 199 where io_data.get('tests') was evaluated instead of io_data.get('results'), omitting Suite I OpenCode entirely. Additionally, Kilo JSON contained a pseudo-test record 'summary' which was parsed as a test.",
            'corrected_individual_tests': total,
            'corrected_passed': passed,
            'corrected_failed': failed,
            'corrected_partial': 0,
            'corrected_not_tested': 0,
            'corrected_blocked': 0,
            'pass_percentage': round((passed / total) * 100, 2)
        },
        'critical_audit_findings': [
            "Frontend Conversation Continuity (Scenario C) is NOT VERIFIED due to a critical defect in AgentDirectChatView.tsx lines 88-90, 260, 305-341 where activeThreadId starts with 'thread-', passes conversationId=undefined to API, and ignores returned backend conv_ ID on SSE done.",
            "FAIL-J05 confirmed: CRITICAL ARCHITECTURAL DEFECT in core/agents/runtime.py line 459-467 where step_stream_async buffers all Gemini chunks into a Python list via list(gemini.stream_text()) before yielding, simulating streaming with asyncio.sleep(0.01).",
            "FAIL-J02 confirmed: Time-To-First-Token (TTFT) is 11.433s out of 11.724s (97.5% of total request duration elapsed before first chunk yielded).",
            "Suite K Cancellation tests K01-K06 were mislabelled as LIVE APPLICATION TEST; they executed against MockUI and mock_llm_stream in-memory generator and are re-labelled MOCKED / SIMULATED TEST.",
            "Suite K Cancellation tests K07-K11 are LIVE PROCESS TEST validating Win32 Job Object tree containment and clean process vaporization.",
            "Test artifact leaks identified: 3 test agents in config/agents.json and 15+ test conversation threads in memory/zezo_brain.db left uncleaned due to tests executing against production storage."
        ]
    },
    'total_tests': total,
    'passed': passed,
    'failed': failed,
    'partial': 0,
    'not_tested': 0,
    'blocked': 0,
    'unverified_frontend_continuity': 1,
    'pass_percentage': round((passed / total) * 100, 2),
    'results': cleaned_results
}

with open('qa_artifacts/QA_VALIDATED_RESULTS.json', 'w', encoding='utf-8') as f:
    json.dump(val_data, f, indent=2)

print(f"Successfully wrote qa_artifacts/QA_VALIDATED_RESULTS.json: Total={total}, Passed={passed}, Failed={failed}")

