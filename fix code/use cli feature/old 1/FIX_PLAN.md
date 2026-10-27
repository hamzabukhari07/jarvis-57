## Batch 1: All Priority 1 problems (critical, blocks portfolio flow)

| Priority | Problem # | Short title | File(s) to change | Est. risk | Depends on | Test to run after fix |
|---|---|---|---|---|---|---|
| 1 | 41 | Fix Fragile Cross-Action Circular Import | actions/fleet_control.py, actions/antigravity_agent.py | high | None | `python -c "import actions.fleet_control, actions.antigravity_agent; print('OK')"` |
| 1 | 1 | Enforce Question Gate For Aliases | actions/fleet_control.py | medium | Problem 41 | `python -c "from actions.fleet_control import _handle_dispatch; res=_handle_dispatch({'agent_id':'ALI','task':'build portfolio'}); assert 'I need to know' in res; print('OK')"` |
| 1 | 33 | Match Build a Portfolio Keywords | actions/fleet_control.py | low | Problem 1 | `python -c "from actions.fleet_control import _handle_dispatch; res=_handle_dispatch({'agent_id':'VERVE','task':'build a portfolio'}); assert 'I need to know' in res; print('OK')"` |
| 1 | 34 | Enforce Greenfield Gate With Path | actions/fleet_control.py | medium | Problem 33 | `python -c "from actions.fleet_control import _handle_dispatch; res=_handle_dispatch({'agent_id':'VERVE','task':'build a portfolio','path':'my_site'}); assert 'I need to know' in res; print('OK')"` |
| 1 | 35 | Silence Greenfield Project Path Warning | actions/fleet_control.py | low | Problem 34 | `python -c "from actions.fleet_control import _handle_dispatch; print('OK')"` |
| 1 | 36 | Fix False Positive Substring Debounce | actions/fleet_control.py | low | None | `python -c "from actions.fleet_control import _RECENT_DISPATCHES; print('OK')"` |
| 1 | 28 | Route Plain Portfolio In Semantics | core/design_resolver.py | medium | None | `python -c "from core.design_resolver import resolve_design; d=resolve_design('build a portfolio'); assert d.is_active(); print('OK')"` |
| 1 | 31 | Align Template Discovery Directory Layout | core/design_resolver.py | medium | None | `python -c "from core.design_resolver import _find_template_file; assert _find_template_file('3_portfolios/Hairline Grid Portfolio.html'); print('OK')"` |
| 1 | 2 | Sanitize Comma Brackets In Matcher | actions/fleet_control.py, core/design_resolver.py | medium | Problem 28 | `python -c "from core.design_resolver import resolve_design; d=resolve_design('portfolio\n[Stack: React, Theme: dark]'); assert d; print('OK')"` |
| 1 | 3 | Strip Agent Persona From Classifier | core/design_resolver.py, core/fleet_manager.py | medium | Problem 28 | `python -c "from core.design_resolver import is_ui_task; assert not is_ui_task('[Ahmad • Backend]\nTask: build db query'); print('OK')"` |
| 1 | 23 | Verify Binary Before File Creation | actions/antigravity_agent.py | low | None | `python -c "from actions.antigravity_agent import _run_worker; print('OK')"` |
| 1 | 25 | Pass Safe Parameters To Worker | core/fleet_manager.py | high | None | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 1 | 27 | Prevent Passing Plain English URLs | core/fleet_manager.py | medium | Problem 25 | `python -c "import re; m=re.search(r'https?://[^\s]+', 'build portfolio'); assert m is None; print('OK')"` |
| 1 | 40 | Forward Portfolio Params Across Tools | actions/fleet_control.py, core/fleet_manager.py | medium | Problem 25 | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 1 | 37 | Preserve Content In Peer Delegation | actions/fleet_control.py, core/fleet_manager.py | medium | Problem 25 | `python -c "from actions.fleet_control import _handle_peer_chat; print('OK')"` |
| 1 | 38 | Isolate Decomposed Workflow Task Paths | actions/fleet_control.py, core/fleet_manager.py | medium | Problem 37 | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |

## Batch 2: All Priority 2 problems (UX, reliability)

| Priority | Problem # | Short title | File(s) to change | Est. risk | Depends on | Test to run after fix |
|---|---|---|---|---|---|---|
| 2 | 6 | Deduplicate WebSocket Start Event Broadcasts | actions/fleet_control.py, core/fleet_manager.py | low | None | `python -c "from actions.fleet_control import _handle_dispatch; print('OK')"` |
| 2 | 19 | Validate Correct Circuit Breaker Tool | core/fleet_manager.py | medium | None | `python -c "from core.circuit_breaker import circuit_breaker; print('OK')"` |
| 2 | 21 | Report Crashed Tasks As Failed | core/fleet_manager.py, actions/fleet_control.py | medium | None | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 2 | 24 | Remove Unconfigured Phantom Agent Spawns | core/fleet_manager.py | low | None | `python -c "from core.fleet_manager import fleet_manager; assert fleet_manager.get_agent('DWIGHT') is not None; print('OK')"` |
| 2 | 26 | Remove Stale Hardcoded User Path | config/fleet_agents.json, core/fleet_manager.py | low | None | `python -c "import json; d=json.load(open('config/fleet_agents.json')); assert 'Hamza' not in str(d); print('OK')"` |
| 2 | 39 | Expose Natural Actions In Schema | actions/fleet_control.py | low | None | `python -c "from actions.fleet_control import TOOL; actions=TOOL['parameters']['properties']['action']['enum']; assert 'delegate' in actions; print('OK')"` |
| 2 | 42 | Retain Permissions When Hiring Agent | actions/fleet_control.py | low | None | `python -c "from actions.fleet_control import _handle_hire; print('OK')"` |
| 2 | 22 | Handle User Cancellation Without Crash | actions/antigravity_agent.py, core/fleet_manager.py | low | Problem 21 | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 2 | 20 | Sandbox Frontend Agent In Worktree | core/fleet_manager.py | medium | Problem 25 | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 2 | 29 | Fix Template Quality Flagship Ranking | core/design_resolver.py, skills/website_build/references/catalog.json | medium | Problem 31 | `python -c "from core.design_resolver import _load_catalog_templates; print('OK')"` |
| 2 | 32 | Single Pass Template Disk Lookup | core/design_resolver.py | low | Problem 31 | `python -c "from core.design_resolver import _find_template_file; print('OK')"` |
| 2 | 4 | Report Web Preview Launch Failures | actions/antigravity_agent.py | low | Problem 23 | `python -c "from actions.antigravity_agent import _try_launch_react_preview; print('OK')"` |
| 2 | 5 | Cache Resolved Design In Worker | actions/antigravity_agent.py | low | Problem 28 | `python -c "from actions.antigravity_agent import resolve_design; print('OK')"` |
| 2 | 30 | Cache Catalog Reading And Scoring | core/design_resolver.py | low | Problem 29 | `python -c "from core.design_resolver import resolve_design; print('OK')"` |

## Batch 3: All Priority 3 problems (dead code, duplicates)

| Priority | Problem # | Short title | File(s) to change | Est. risk | Depends on | Test to run after fix |
|---|---|---|---|---|---|---|
| 3 | 7 | Cache Action Registry Disk Scans | core/fleet_manager.py | low | None | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 3 | 12 | Delete Unused Fleet Module Functions | core/fleet_manager.py | low | None | `python -c "import core.fleet_manager; print('OK')"` |
| 3 | 14 | Remove Dead Variable Assignment Source | actions/antigravity_agent.py | low | None | `python -c "import actions.antigravity_agent; print('OK')"` |
| 3 | 15 | Eliminate Redundant Null Handle Assignment | actions/antigravity_agent.py | low | None | `python -c "import actions.antigravity_agent; print('OK')"` |
| 3 | 17 | Prune Unread Design Color Attributes | core/design_resolver.py | low | None | `python -c "from core.design_resolver import ResolvedDesign; print('OK')"` |
| 3 | 18 | Remove Dead Design Prompt Formatter | core/design_resolver.py | low | None | `python -c "import core.design_resolver; print('OK')"` |
| 3 | 13 | Remove Unused Greenfield Caller Parameter | actions/antigravity_agent.py, actions/fleet_control.py | low | Problem 41 | `python -c "from actions.antigravity_agent import check_greenfield_gate; print('OK')"` |
| 3 | 8 | Unify Prompt Spec Formatting Logic | actions/fleet_control.py, actions/antigravity_agent.py | low | Problem 2 | `python -c "from actions.antigravity_agent import _run_worker; print('OK')"` |
| 3 | 10 | Consolidate Worktree Teardown Cleanup Logic | core/fleet_manager.py | low | Problem 21 | `python -c "from core.fleet_manager import fleet_manager; print('OK')"` |
| 3 | 11 | Remove Redundant Consecutive Cancellation Check | actions/antigravity_agent.py | low | Problem 22 | `python -c "from actions.antigravity_agent import _run_worker; print('OK')"` |
| 3 | 16 | Clean Discarded Template Discovery Directories | core/design_resolver.py | low | Problem 31 | `python -c "from core.design_resolver import _get_ui_dirs; print('OK')"` |
| 3 | 9 | Load Catalog From Config Only | core/design_resolver.py, skills/website_build/references/catalog.json | low | Problem 29 | `python -c "from core.design_resolver import _load_catalog_templates; print('OK')"` |
