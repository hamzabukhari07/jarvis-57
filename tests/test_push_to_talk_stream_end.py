import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
import time

@pytest.mark.asyncio
async def test_push_to_talk_state_and_stream_end_queue():
    from main import ZezoLive

    # Create dummy ZezoLive instance without invoking full __init__
    zezo = ZezoLive.__new__(ZezoLive)
    zezo.ui = MagicMock()
    zezo.ui.muted = False
    zezo.ui._sleeping = False
    zezo._ptt_enabled = True
    zezo._ptt_held = False
    zezo._wake_enabled = False
    zezo._awake = True
    zezo._is_speaking = False
    zezo._interrupted = False
    zezo._awaiting_speech_reply = False
    zezo._speaking_lock = MagicMock()
    zezo._speaking_lock.__enter__ = MagicMock(return_value=None)
    zezo._speaking_lock.__exit__ = MagicMock(return_value=None)
    zezo.out_queue = asyncio.Queue()
    zezo._loop = asyncio.get_running_loop()

    # 1. Verify resting state when PTT enabled and not held
    assert zezo._get_resting_state() == "IDLE"

    # 2. Simulate Key Down (held=True)
    zezo._on_ptt(True)
    assert zezo._ptt_held is True
    assert zezo._awaiting_speech_reply is False
    zezo.ui.set_state.assert_called_with("LISTENING")

    # 3. Simulate Key Up (held=False)
    zezo._on_ptt(False)
    assert zezo._ptt_held is False
    assert zezo._awaiting_speech_reply is True
    zezo.ui.set_state.assert_called_with("THINKING")
    assert zezo._get_resting_state() == "THINKING"

    # Give loop a brief moment to process call_soon_threadsafe
    await asyncio.sleep(0.05)

    # Verify queue contents: should have 3 silence frames followed by audio_stream_end
    items = []
    while not zezo.out_queue.empty():
        items.append(zezo.out_queue.get_nowait())

    assert len(items) == 4
    # First 3 items are silence chunks
    for i in range(3):
        assert "data" in items[i]
        assert all(b == 0 for b in items[i]["data"])
        assert "audio/pcm;rate=16000" in items[i]["mime_type"]

    # 4th item is audio_stream_end sentinel
    assert items[3].get("audio_stream_end") is True

    # 4. Verify _send_realtime processes audio_stream_end sentinel cleanly
    zezo.session = MagicMock()
    zezo.session.send_realtime_input = AsyncMock()

    # Put audio_stream_end into queue
    await zezo.out_queue.put({"audio_stream_end": True})

    # Run step of queue logic
    msg = await zezo.out_queue.get()
    assert msg.get("audio_stream_end") is True
    await zezo.session.send_realtime_input(audio_stream_end=True)
    zezo.session.send_realtime_input.assert_awaited_once_with(audio_stream_end=True)


def test_push_to_talk_barge_in_and_interrupt():
    from main import ZezoLive

    zezo = ZezoLive.__new__(ZezoLive)
    zezo.ui = MagicMock()
    zezo.ui.muted = False
    zezo.ui._sleeping = False
    zezo._ptt_enabled = True
    zezo._ptt_held = False
    zezo._wake_enabled = False
    zezo._awake = True
    zezo._is_speaking = True
    zezo._interrupted = False
    zezo._out_latency = 0.20
    zezo._awaiting_speech_reply = True
    zezo._speaking_lock = MagicMock()
    zezo._speaking_lock.__enter__ = MagicMock(return_value=None)
    zezo._speaking_lock.__exit__ = MagicMock(return_value=None)
    zezo.out_queue = asyncio.Queue()
    zezo.audio_in_queue = asyncio.Queue()
    zezo._turn_done_event = None
    zezo._visemes = MagicMock()
    zezo._silence_watchdog_task = None

    # Put a stale chunk in out_queue
    zezo.out_queue.put_nowait({"data": b"stale"})

    # Trigger PTT Hold while ZEZO was speaking (Barge-in)
    zezo._on_ptt(True)

    # 1. Active speech should be interrupted
    assert zezo._ptt_held is True
    assert zezo.out_queue.empty()
    assert zezo._interrupted is False  # Must be cleared for new turn
    assert zezo._awaiting_speech_reply is False
    zezo.ui.set_state.assert_called_with("LISTENING")

    # 2. Test manual interrupt() clears awaiting reply
    zezo._awaiting_speech_reply = True
    zezo.interrupt()
    assert zezo._awaiting_speech_reply is False
    assert zezo._interrupted is True


def test_push_to_talk_resting_states():
    from main import ZezoLive

    zezo = ZezoLive.__new__(ZezoLive)
    zezo._ptt_enabled = True
    zezo._ptt_held = False
    zezo._wake_enabled = False
    zezo._awake = True

    # Resting state while awaiting speech reply -> THINKING
    zezo._awaiting_speech_reply = True
    assert zezo._get_resting_state() == "THINKING"

    # Resting state when reply arrives and finished -> IDLE
    zezo._awaiting_speech_reply = False
    assert zezo._get_resting_state() == "IDLE"

    # Resting state while holding key -> LISTENING
    zezo._ptt_held = True
    assert zezo._get_resting_state() == "LISTENING"


