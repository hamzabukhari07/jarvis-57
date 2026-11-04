# QA Cleanup Candidates Inventory & Audit Report

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Date of Audit:** November 4, 2026  
> **Status:** AUDIT COMPLETE — PENDING LEAD ARCHITECT REVIEW  
> **Safety Rule Applied:** READ-ONLY INVENTORY. ZERO records or agents were modified or deleted.  

---

## 1. Executive Summary

During the extensive Phase 1 & Phase 2 QA verification passes conducted on November 4, 2026, several ephemeral test entities and synthetic test conversations were created across:
1. `config/agents.json`: 3 test agent definitions leaked into configuration during tier boundary and capability tests.
2. `memory/zezo_brain.db`: 108 test conversation records and 434 associated messages generated across testing suites (Suite D stream interrupt/rapid messaging, Suite E context sync/memory persistence, Suite G boundary enforcement, Suite J persistence, and cross-agent isolation verification).

Before running any database cleanup scripts or editing configuration files, full timestamped physical backups were verified, and this granular audit document was compiled for Hamza Bukhari's review.

---

## 2. Backup Verification

Physical byte-level backups were created and verified prior to generating this inventory:

| Backup File Path | File Size | Description | Integrity Status |
| :--- | :--- | :--- | :--- |
| `qa_backups/agents_20261104_215132.json` | 16,754 bytes | Snapshot of `config/agents.json` prior to any remediation | Verified valid JSON |
| `qa_backups/zezo_brain_20261104_215132.db` | 528,384 bytes | SQLite binary copy of `memory/zezo_brain.db` | Verified valid SQLite DB |

---

## 3. Leaked Test Agents in `config/agents.json`

The following 3 agent records were identified in `config/agents.json`. None of these are core production agents (`MICHAEL`, `VERVE`, `FLUX`, `AHMAD`, `DWIGHT` remain untouched).

### Leaked Agent Inventory

| Agent Key / ID | Agent Name | Risk Tier | Allowed Tools / Skills | Leaked Source / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `TEST_RESTRICTED_ATTE` | `Restricted Attempt Agent` | `L0_READ_ONLY` | Tools: `['web_search']`<br>Skills: `['opencode', 'multi_agent_collaboration', 'make_plan', 'git_workflow']` | Created during Suite G L0-tier tool constraint & skill boundary testing. Has zero conversations/messages in DB. |
| `SECURITY_AUDIT_L0` | `Security Audit L0` | `L0_READ_ONLY` | Tools: `['web_search', 'task_status']`<br>Skills: `[]` | Created during Suite G permission denial testing. Has zero conversations/messages in DB. |
| `SNEAKYL0AGENT` | `Sneaky L0 Agent` | `L0_READ_ONLY` | Tools: `['web_search']`<br>Skills: `['web_scraper', 'social_research', 'web_research_pipeline']` | Created during Suite G risk elevation audit. Has zero conversations/messages in DB. |

### Configuration Safety Assessment
- **Conversation / Message Association:** `SELECT count(1) FROM agent_conversations WHERE agent_id IN ('TEST_RESTRICTED_ATTE', 'SECURITY_AUDIT_L0', 'SNEAKYL0AGENT')` returns **0**.
- **Impact of Removal:** Safe to delete keys from `config/agents.json`. No foreign key or database integrity constraints are linked to these 3 agent IDs.

---

## 4. Database Candidates Inventory (`memory/zezo_brain.db`)

A query of `agent_conversations` and `agent_messages` on 2026-11-04 reveals:
- **Total Conversations on 2026-11-04:** 108 records
- **Total Messages on 2026-11-04:** 434 records

### Breakdown by Agent

| Agent ID | Conversations Count | Messages Count | Category / Origin |
| :--- | :--- | :--- | :--- |
| `MICHAEL` | 73 | 347 | QA Test Suites (D, E, J, Stream, Rapid, SaaS Test prompts) |
| `VERVE` | 12 | 43 | QA Tool Failure / Stream Loop / Prompt Tests |
| `ZEZO` | 3 | 21 | Stream Interrupt, Rapid Message, Integrity Tests |
| `AGENT_ALPHA` | 2 | 2 | Isolation & Cross-Agent Leak Tests (`conv_agent1_*`) |
| `AGENT_BETA` | 4 | 0 | Isolation & Cross-Agent Leak Tests (`conv_agent2_*`) |
| `QA_SUITE_B_BOT` | 2 | 4 | Suite B Ephemeral Agent Test |
| `QA_SUITE_G` | 1 | 3 | Suite G L0 Enforcement Test |
| `QA_SUITE_G_TEST` | 1 | 3 | Suite G Tool Denial Test |
| `QA_SUITE_G_TEST2` | 1 | 3 | Suite G Bounds Test |
| `QA_SUITE_G_BOUNDS`| 1 | 2 | Suite G Bounds Test |
| `ZEZO_QA_AGENT` | 1 | 2 | QA Agent Creation Test |
| `QA_SUITE_G_DENIED`| 1 | 1 | Suite G Permission Denied Test |
| `DWIGHT` | 4 | 2 | Dwight Solo / Isolation Test |
| `QA_OTH_1189BF` | 1 | 0 | Ephemeral ID Agent Test |
| **Total** | **108** | **434** | — |

---

## 5. Granular Categorization of Conversations

### Category A: Ephemeral / Synthetic QA Agents (15 Conversations, 20 Messages)
These conversations were created under temporary agent IDs used exclusively for testing security boundaries, permissions, and cross-agent isolation:

| Conversation ID | Agent ID | Title | Created At (UTC) | Msg Count | Content Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `conv_6782b944b176` | `ZEZO_QA_AGENT` | New Conversation | 2026-11-04 15:19:40 | 2 | QA Agent test prompt |
| `conv_efbe62bc766a` | `QA_SUITE_G` | New Conversation | 2026-11-04 15:20:39 | 3 | Suite G security test |
| `conv_1a0dcb306eb3` | `QA_SUITE_B_BOT` | New Conversation | 2026-11-04 15:21:14 | 2 | Suite B test prompt |
| `conv_0bd655c919e6` | `QA_SUITE_G_TEST` | New Conversation | 2026-11-04 15:21:40 | 3 | Suite G test prompt |
| `conv_89ab9257ca66` | `QA_SUITE_G_TEST2` | New Conversation | 2026-11-04 15:22:26 | 3 | Suite G test prompt |
| `conv_2b7db47169b6` | `QA_SUITE_G_DENIED`| New Conversation | 2026-11-04 15:22:50 | 1 | Tool denial test |
| `conv_ba00848aa697` | `QA_SUITE_G_BOUNDS`| New Conversation | 2026-11-04 15:23:30 | 2 | Bounds verification |
| `conv_038c43650509` | `QA_SUITE_B_BOT` | New Conversation | 2026-11-04 15:23:46 | 2 | Suite B test prompt |
| `conv_edb60584af7f` | `AGENT_BETA` | New Conversation | 2026-11-04 15:27:36 | 0 | Cross-agent test thread |
| `conv_b36199a17376` | `QA_OTH_1189BF` | New Conversation | 2026-11-04 15:27:50 | 0 | Ephemeral bot test |
| `conv_8e3504998650` | `AGENT_BETA` | New Conversation | 2026-11-04 15:29:22 | 0 | Cross-agent test thread |
| `conv_agent1_ca93ae5b` | `AGENT_ALPHA` | Alpha Thread | 2026-11-04 20:27:35 | 1 | Isolation probe: `ALPHA_TOP_SECRET_MEMORY` |
| `conv_agent2_2759b70b` | `AGENT_BETA` | Beta Thread | 2026-11-04 20:27:35 | 0 | Isolation target |
| `conv_agent1_34ebbdc9` | `AGENT_ALPHA` | Alpha Thread | 2026-11-04 20:29:22 | 1 | Isolation probe: `ALPHA_TOP_SECRET_MEMORY` |
| `conv_agent2_43a19ae5` | `AGENT_BETA` | Beta Thread | 2026-11-04 20:29:22 | 0 | Isolation target |

---

### Category B: Named Test Suites under Core Agents (48 Conversations, 303 Messages)
These conversations were explicitly titled with test suite identifiers to verify stream interruption, context synchronization, long conversational histories, ordering, and fact retention:

| Conversation ID | Agent ID | Title | Created At (UTC) | Msg Count |
| :--- | :--- | :--- | :--- | :--- |
| `conv_bd038bc6f7f7` | `MICHAEL` | Test Conversation | 2026-11-04 15:13:08 | 2 |
| `conv_ed61d88ae65a` | `MICHAEL` | Stream Test | 2026-11-04 15:13:24 | 1 |
| `conv_8ee62d9946de` | `MICHAEL` | Stream Test 2 | 2026-11-04 15:14:32 | 1 |
| `conv_b9f264e5cb46` | `MICHAEL` | Alex SaaS Test | 2026-11-04 15:21:33 | 2 |
| `conv_763a48169354` | `MICHAEL` | Alex SaaS Test | 2026-11-04 15:21:46 | 4 |
| `conv_fbbebc933905` | `MICHAEL` | Stream test | 2026-11-04 15:22:08 | 4 |
| `conv_184e03f5bcdc` | `MICHAEL` | Test Conv | 2026-11-04 15:23:42 | 1 |
| `conv_a97f81784c97` | `ZEZO` | Stream Interrupt Test | 2026-11-04 15:23:43 | 1 |
| `conv_c7cb6b22951a` | `ZEZO` | Rapid Messages Test | 2026-11-04 15:23:43 | 15 |
| `conv_31e11892ac0d` | `ZEZO` | Integrity Verification Test | 2026-11-04 15:23:44 | 5 |
| `conv_3c2cffbe01bd` | `MICHAEL` | Stream Context Check | 2026-11-04 15:23:56 | 4 |
| `conv_8975b3f52585` | `MICHAEL` | Suite J Persistence Test | 2026-11-04 15:24:35 | 2 |
| `conv_d862b076c0f2` | `MICHAEL` | Suite J Long Req | 2026-11-04 15:25:16 | 2 |
| `conv_c1f21f36afb5` | `MICHAEL` | Alex Dental SaaS Project | 2026-11-04 15:25:17 | 4 |
| `conv_53c4cf46faff` | `MICHAEL` | E01 Conv | 2026-11-04 15:25:17 | 3 |
| `conv_ef9dc0eaff09` | `MICHAEL` | E02 History | 2026-11-04 15:25:17 | 4 |
| `conv_9e6d4209c4e8` | `MICHAEL` | E03 Persistence | 2026-11-04 15:25:17 | 10 |
| `conv_fb12a74997e9` | `MICHAEL` | E04 Ordering | 2026-11-04 15:25:17 | 5 |
| `conv_8464e3184322` | `MICHAEL` | E05 Long Convo | 2026-11-04 15:25:17 | 60 |
| `conv_89e55919c4d2` | `MICHAEL` | E07 Prompt Check | 2026-11-04 15:25:17 | 1 |
| `conv_9b24f06eba6b` | `MICHAEL` | E08 Workspace Check | 2026-11-04 15:25:17 | 2 |
| `conv_6b45656921c7` | `MICHAEL` | Conv Alpha | 2026-11-04 15:25:17 | 2 |
| `conv_acfca266b9dc` | `MICHAEL` | Michael Solo | 2026-11-04 15:25:17 | 1 |
| `conv_935737d4890f` | `DWIGHT` | Dwight Solo | 2026-11-04 15:25:17 | 1 |
| `conv_bdb94b039949` | `MICHAEL` | E11 Facts vs Assumptions | 2026-11-04 15:25:18 | 2 |
| `conv_9ac1a5836822` | `MICHAEL` | E12 Unknown Info | 2026-11-04 15:25:18 | 2 |
| `conv_e66c5fb88cc7` | `MICHAEL` | E13 Sync Stream Context | 2026-11-04 15:25:18 | 4 |
| `conv_2c3301b11f15` | `MICHAEL` | Michael Confidential | 2026-11-04 15:25:18 | 0 |
| `conv_99f0e49e48ed` | `MICHAEL` | Conv Alpha | 2026-11-04 15:25:54 | 0 |
| `conv_f86c049d1b49` | `MICHAEL` | Alex Dental SaaS Project | 2026-11-04 15:26:17 | 4 |
| `conv_85b8347cee0e` | `MICHAEL` | E01 Conv | 2026-11-04 15:26:17 | 3 |
| `conv_8ff2af8062e1` | `MICHAEL` | E02 History | 2026-11-04 15:26:17 | 4 |
| `conv_a77c23ba1d8f` | `MICHAEL` | E03 Persistence | 2026-11-04 15:26:17 | 10 |
| `conv_dcb1130167dc` | `MICHAEL` | E04 Ordering | 2026-11-04 15:26:17 | 5 |
| `conv_d0ad20a6365b` | `MICHAEL` | E05 Long Convo | 2026-11-04 15:26:17 | 60 |
| `conv_894532319950` | `MICHAEL` | E07 Prompt Check | 2026-11-04 15:26:17 | 1 |
| `conv_12e54c4cb88f` | `MICHAEL` | E08 Workspace Check | 2026-11-04 15:26:17 | 2 |
| `conv_b7b766b5032a` | `MICHAEL` | Conv Alpha | 2026-11-04 15:26:17 | 1 |
| `conv_177f32c73de1` | `MICHAEL` | Conv Beta | 2026-11-04 15:26:17 | 1 |
| `conv_356cec9b2c40` | `MICHAEL` | Michael Solo | 2026-11-04 15:26:17 | 1 |
| `conv_215de3e2aafb` | `DWIGHT` | Dwight Solo | 2026-11-04 15:26:17 | 1 |
| `conv_b189fa7447da` | `MICHAEL` | E11 Facts vs Assumptions | 2026-11-04 15:26:17 | 2 |
| `conv_e1c01872377d` | `MICHAEL` | E12 Unknown Info | 2026-11-04 15:26:17 | 2 |
| `conv_2f68dd619587` | `MICHAEL` | E13 Sync Stream Context | 2026-11-04 15:26:17 | 4 |
| `conv_9b03bea3483b` | `MICHAEL` | Michael Confidential | 2026-11-04 15:26:17 | 0 |
| `conv_c3eac40a5769` | `MICHAEL` | Suite D Verification Thread | 2026-11-04 15:27:27 | 20 |
| `conv_92fa65f02ea5` | `MICHAEL` | Stream Interrupt Test | 2026-11-04 15:28:32 | 1 |
| `conv_6becb23b9799` | `MICHAEL` | Rapid Messages Test | 2026-11-04 15:28:32 | 15 |
| `conv_6a9c654357c5` | `MICHAEL` | Integrity Verification Test | 2026-11-04 15:28:33 | 5 |
| `conv_1de754160a93` | `MICHAEL` | Suite D Verification Thread | 2026-11-04 15:31:06 | 20 |

---

### Category C: Unnamed Synthetic Test Threads ("New Conversation") (45 Conversations, 111 Messages)
These conversations were instantiated during rapid test harnesses with default title `"New Conversation"`. Each contains synthetic QA test inputs (e.g. simulated tool failures `"Trigger failing tool"`, `"Loop forever"`, or basic role prompt tests):

| Conversation ID | Agent ID | Created At (UTC) | Msg Count | Sample Content / Test Role |
| :--- | :--- | :--- | :--- | :--- |
| `conv_ec33c98878fb` | `MICHAEL` | 2026-11-04 14:55:26 | 2 | Role intro check |
| `conv_acde7eb29ac6` | `MICHAEL` | 2026-11-04 14:57:15 | 2 | Alex dentist project context test |
| `conv_855a789de13e` | `MICHAEL` | 2026-11-04 14:57:53 | 2 | Short question test |
| `conv_99c5964ccd02` | `VERVE` | 2026-11-04 15:01:44 | 2 | Role response check |
| `conv_151f20fea6aa` | `VERVE` | 2026-11-04 15:02:26 | 2 | Role response check |
| `conv_239587943eba` | `MICHAEL` | 2026-11-04 15:18:09 | 2 | Basic prompt test |
| `conv_a06b802a0d89` | `MICHAEL` | 2026-11-04 15:18:57 | 2 | Basic prompt test |
| `conv_57b364cde5e3` | `MICHAEL` | 2026-11-04 15:20:32 | 2 | Synthetic prompt test |
| `conv_916112379771` | `MICHAEL` | 2026-11-04 15:21:25 | 0 | Empty test thread |
| `conv_8816b61b269a` | `MICHAEL` | 2026-11-04 15:21:33 | 4 | 2-turn dialogue test |
| `conv_0e2304acc1af` | `MICHAEL` | 2026-11-04 15:21:44 | 2 | Synthetic prompt test |
| `conv_4e95a63ebea8` | `MICHAEL` | 2026-11-04 15:22:03 | 2 | Synthetic prompt test |
| `conv_71ff2c0253f4` | `MICHAEL` | 2026-11-04 15:22:10 | 2 | Synthetic prompt test |
| `conv_9a459f0d2a13` | `MICHAEL` | 2026-11-04 15:22:25 | 2 | Synthetic prompt test |
| `conv_36f7019d759e` | `MICHAEL` | 2026-11-04 15:22:37 | 2 | Synthetic prompt test |
| `conv_e8e8b76dbca0` | `MICHAEL` | 2026-11-04 15:23:26 | 2 | Synthetic prompt test |
| `conv_f100a8a95f53` | `MICHAEL` | 2026-11-04 15:23:28 | 10 | 5-turn multi-turn test |
| `conv_eb251bdc6a90` | `MICHAEL` | 2026-11-04 15:23:29 | 1 | Uncompleted single message test |
| `conv_371817d9d8b4` | `VERVE` | 2026-11-04 15:24:13 | 5 | Infinite loop breaker test (`Loop forever`) |
| `conv_a01f41305952` | `VERVE` | 2026-11-04 15:24:37 | 2 | Synthetic prompt test |
| `conv_deaa3ba2ff84` | `VERVE` | 2026-11-04 15:24:48 | 2 | Synthetic prompt test |
| `conv_2c4b9afb8ea2` | `DWIGHT` | 2026-11-04 15:25:18 | 0 | Empty test thread |
| `conv_c270f53afa2e` | `MICHAEL` | 2026-11-04 15:25:28 | 2 | Synthetic prompt test |
| `conv_c7e8fc1767ea` | `VERVE` | 2026-11-04 15:25:50 | 8 | Multi-turn streaming test |
| `conv_28988d61a183` | `DWIGHT` | 2026-11-04 15:26:17 | 0 | Empty test thread |
| `conv_8d2e629635ef` | `VERVE` | 2026-11-04 15:26:32 | 8 | Multi-turn streaming test |
| `conv_49461b1ac83e` | `VERVE` | 2026-11-04 15:26:39 | 3 | Tool error handling test (`Trigger failing tool`) |
| `conv_2ece437057ff` | `VERVE` | 2026-11-04 15:26:39 | 5 | Tool error recovery test |
| `conv_703273861d73` | `VERVE` | 2026-11-04 15:26:39 | 2 | Tool error recovery test |
| `conv_81a593a41091` | `MICHAEL` | 2026-11-04 15:29:03 | 2 | Synthetic prompt test |
| `conv_1fd6d091846e` | `VERVE` | 2026-11-04 15:29:13 | 2 | Synthetic prompt test |
| `conv_8ae5c1c9298a` | `MICHAEL` | 2026-11-04 15:29:19 | 2 | Synthetic prompt test |
| `conv_6b3d0ab8a990` | `MICHAEL` | 2026-11-04 15:29:24 | 2 | Synthetic prompt test |
| `conv_0ab35e3879b4` | `MICHAEL` | 2026-11-04 15:30:08 | 2 | Synthetic prompt test |
| `conv_227b142cf9cc` | `MICHAEL` | 2026-11-04 15:30:17 | 2 | Synthetic prompt test |
| `conv_8fac6566f37c` | `MICHAEL` | 2026-11-04 15:30:22 | 2 | Synthetic prompt test |
| `conv_4e6e74fefef0` | `MICHAEL` | 2026-11-04 15:32:33 | 2 | Synthetic prompt test |
| `conv_2ee1a749f2ab` | `VERVE` | 2026-11-04 15:32:33 | 2 | Synthetic prompt test |
| `conv_a3009e62fa5e` | `MICHAEL` | 2026-11-04 15:32:42 | 2 | Synthetic prompt test |
| `conv_982861bc9287` | `MICHAEL` | 2026-11-04 15:32:48 | 2 | One-sentence summary test |
| `conv_a594fae4d821` | `MICHAEL` | 2026-11-04 16:56:14 | 2 | Post-fix run test |
| `conv_0f2da710c58e` | `MICHAEL` | 2026-11-04 16:56:22 | 2 | Post-fix run test |
| `conv_30a2c06efa87` | `MICHAEL` | 2026-11-04 16:56:56 | 2 | Post-fix run test |

---

## 6. Safety Recommendations for Hamza Bukhari

### Recommendation 1: Removing Leaked Agents from `config/agents.json`
- **Action:** Delete the keys `"TEST_RESTRICTED_ATTE"`, `"SECURITY_AUDIT_L0"`, and `"SNEAKYL0AGENT"` from `config/agents.json`.
- **Safety Proof:** Verified zero SQLite foreign key relationships or message dependencies exist in `memory/zezo_brain.db`.
- **Risk Level:** **Very Low**. Restores `config/agents.json` to its clean production baseline.

### Recommendation 2: Purging Ephemeral QA Agent Records (Category A)
- **Scope:** 15 conversations and 20 messages linked to test agent IDs (`AGENT_ALPHA`, `AGENT_BETA`, `QA_SUITE_*`, `ZEZO_QA_AGENT`, `QA_OTH_*`).
- **SQL Preview:**
  ```sql
  DELETE FROM agent_messages WHERE conversation_id IN (
      SELECT id FROM agent_conversations WHERE agent_id IN (
          'AGENT_ALPHA', 'AGENT_BETA', 'QA_SUITE_B_BOT', 'QA_SUITE_G', 
          'QA_SUITE_G_TEST', 'QA_SUITE_G_TEST2', 'QA_SUITE_G_DENIED', 
          'QA_SUITE_G_BOUNDS', 'ZEZO_QA_AGENT', 'QA_OTH_1189BF'
      )
  );
  DELETE FROM agent_conversations WHERE agent_id IN (
      'AGENT_ALPHA', 'AGENT_BETA', 'QA_SUITE_B_BOT', 'QA_SUITE_G', 
      'QA_SUITE_G_TEST', 'QA_SUITE_G_TEST2', 'QA_SUITE_G_DENIED', 
      'QA_SUITE_G_BOUNDS', 'ZEZO_QA_AGENT', 'QA_OTH_1189BF'
  );
  ```
- **Risk Level:** **Zero Risk to Production**. These agents do not exist in the production roster.

### Recommendation 3: Archiving vs Deleting Category B & Category C Test Runs
- **Option 1 (Full Clean Slate to Pre-QA State):** Delete all 108 conversations and 434 messages created on `2026-11-04`. This resets `agent_conversations` back to the 46 conversations from November 3, 2026.
- **Option 2 (Archive Flag):** Rather than hard-deleting Category B & C records under `MICHAEL` and `VERVE`, set `is_archived = 1` so they remain hidden from the UI conversation list while preserving audit history:
  ```sql
  UPDATE agent_conversations SET is_archived = 1 WHERE created_at LIKE '2026-11-04%';
  ```
- **Option 3 (Selective Hard Delete):** Hard delete Category A (ephemeral agents) + Category C (unnamed dummy runs), leaving only intentionally documented test fixtures if needed.

### Integrity Summary Table

| Subsystem | Baseline (Nov 3) | Current Leaked/QA State | Clean Slate Target |
| :--- | :--- | :--- | :--- |
| `config/agents.json` | 6 agents | 9 agents (+3 leaked test agents) | 6 agents |
| `agent_conversations` | 46 rows | 154 rows (+108 QA rows) | 46 rows |
| `agent_messages` | 102 rows | 536 rows (+434 QA rows) | 102 rows |

---

*Report prepared autonomously by ZEZO QA Senior Architect for Hamza Bukhari.*
