"""
tests/test_p0_interrupt_and_doom_loop.py — Regression tests for P0 fixes:
1. Tool call and tool result persistence across interrupts in conversation transcript/session log.
2. Doom-Loop guard firing on 2 identical invocations in a row with strategy-change coaching feedback.
"""

import unittest
from unittest.mock import MagicMock, patch
import asyncio

from core.loop_gates import GateDecision, LoopGatesEngine, loop_gates
from core import action_loader


class TestP0InterruptAndDoomLoop(unittest.TestCase):

    def setUp(self):
        # Reset global loop gate session for isolation
        loop_gates.reset_session("global")
        loop_gates.reset_session("test_session")

    def test_doom_loop_guard_fires_on_2_identical_calls(self):
        """Verify that 2 identical tool calls in a row trigger the doom loop guard."""
        engine = LoopGatesEngine() # defaults to similarity_threshold=1
        session_id = "test_sess"
        params = {"direction": "up", "amount": 100, "action": "scroll"}

        # Call 1: Must PROCEED
        res1 = engine.evaluate("computer_control", params, session_id=session_id)
        self.assertEqual(res1.decision, GateDecision.PROCEED)

        # Call 2 (identical arguments in a row): Must trigger INTERRUPT
        res2 = engine.evaluate("computer_control", params, session_id=session_id)
        self.assertEqual(res2.decision, GateDecision.INTERRUPT)
        self.assertIn("Doom-Loop detected: 2 identical invocations of 'computer_control'", res2.reason)
        self.assertIn("You already called 'computer_control' with these exact arguments and it succeeded", res2.coaching_feedback)
        self.assertIn("Use screen_process to verify, or ask the user what they want", res2.coaching_feedback)

    def test_action_loader_returns_coaching_on_second_identical_call(self):
        """Verify action_loader returns coaching text when doom-loop guard triggers on 2nd call."""
        from core.action_loader import get_action_registry
        registry = get_action_registry()
        params = {"direction": "up", "amount": 100, "action": "scroll"}
        ctx = {"session_id": "test_loader_sess"}

        # Call 1
        with patch("core.action_loader._call_handler", return_value="Scrolled up x100"):
            res1 = registry.run("computer_control", params, ctx=ctx)
            self.assertEqual(res1, "Scrolled up x100")

        # Call 2 (identical)
        with patch("core.action_loader._call_handler", return_value="Scrolled up x100"):
            res2 = registry.run("computer_control", params, ctx=ctx)
            self.assertIn("⚠️ [DOOM-LOOP INTERRUPT]", res2)
            self.assertIn("You already called 'computer_control' with these exact arguments and it succeeded", res2)

    def test_tool_result_persistence_across_interrupt(self):
        """
        Simulate: user utterance -> LLM tool call -> tool result -> interrupt -> turn_complete.
        Assert that the session log contains:
        1. User utterance
        2. Tool call
        3. Tool result
        and tool_busy / awaiting_tool_reply are cleanly reset (not stuck in thinking).
        """
        from main import ZezoLive

        # Initialize mock ZezoLive instance without full device loop
        asst = ZezoLive.__new__(ZezoLive)
        asst._session_log = []
        asst._last_user_in_logged = ""
        asst.audio_in_queue = asyncio.Queue()
        asst.out_queue = asyncio.Queue()
        asst._speaking_lock = unittest.mock.MagicMock()
        asst._is_speaking = False
        asst._visemes = MagicMock()
        asst._turn_done_event = None
        asst.ui = MagicMock()
        asst.ui.muted = False
        asst.ui._sleeping = False
        asst._silence_watchdog_task = None
        asst._ptt_watchdog_task = None
        asst._awaiting_speech_reply = True
        asst._awaiting_tool_reply = False
        asst._tool_busy = False
        asst._interrupted = False
        asst._get_resting_state = MagicMock(return_value="IDLE")

        # Step 1: User speaks "full or top kar"
        user_speech = "full or top kar"
        in_buf = [user_speech]
        in_logged = False

        # Step 2: LLM issues tool call computer_control(scroll up 100)
        # Directly execute _execute_tool recording logic
        tool_name = "computer_control"
        tool_args = {"direction": "up", "amount": 100, "action": "scroll"}
        tool_result = "Scrolled up x100"

        # Emulate _execute_tool appending to session_log
        asst._session_log.append(f"Tool call: {tool_name}({tool_args})")
        asst._session_log.append(f"Tool result: {tool_name} → {tool_result}")
        asst._awaiting_tool_reply = True

        # Step 3: Audio arrives and then interrupt is triggered
        asst.audio_in_queue.put_nowait(b"dummy_pcm_chunk_1")
        asst.audio_in_queue.put_nowait(b"dummy_pcm_chunk_2")

        # Simulate server_content.interrupted
        asst._interrupted = True
        asst.interrupt()

        # Verify interrupt cleared audio buffer but NOT session_log
        self.assertTrue(asst.audio_in_queue.empty())
        self.assertFalse(asst._awaiting_tool_reply)
        self.assertFalse(asst._tool_busy)
        asst.ui.set_state.assert_called_with("IDLE")

        # Step 4: Simulate turn_complete ending the interrupted turn
        if asst._end_interrupted_turn():
            full_in = " ".join(in_buf).strip()
            if full_in and not in_logged:
                asst._last_user_in_logged = full_in
                asst._session_log.append(f"User: {full_in}")
            in_buf = []

        # Step 5: Assert next turn transcript / session_log preserves all context
        self.assertTrue(any("User: full or top kar" in entry for entry in asst._session_log))
        self.assertTrue(any("Tool call: computer_control" in entry for entry in asst._session_log))
        self.assertTrue(any("Tool result: computer_control → Scrolled up x100" in entry for entry in asst._session_log))
        self.assertEqual(len(asst._session_log), 3)


if __name__ == "__main__":
    unittest.main()
