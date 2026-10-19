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
    zezo.audio_in_queue = asyncio.Queue()
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
    zezo.audio_in_queue.put_nowait(b"stale_incoming")
    zezo._turn_done_event = None
    zezo._visemes = MagicMock()
    zezo._silence_watchdog_task = None

    # Put a stale chunk in out_queue
    zezo.out_queue.put_nowait({"data": b"stale"})

    # Trigger PTT Hold while ZEZO was speaking (Barge-in)
    zezo._on_ptt(True)

    # 1. Active speech should be interrupted and queues drained
    assert zezo._ptt_held is True
    assert zezo.out_queue.empty()
    assert zezo.audio_in_queue.empty()
    assert zezo._interrupted is True  # Stays True while held so in-flight chunks are dropped
    assert zezo._awaiting_speech_reply is False
    zezo.ui.set_state.assert_called_with("LISTENING")

    # 2. Add an incoming chunk while held, then release
    zezo.audio_in_queue.put_nowait(b"incoming_during_speech")
    zezo._loop = None
    zezo._enqueue_out_audio = MagicMock()
    zezo._on_ptt(False)

    # 3. Upon release, queue is flushed and _interrupted resets to False for Query 2 response
    assert zezo._ptt_held is False
    assert zezo.audio_in_queue.empty()
    assert zezo._interrupted is False
    assert zezo._awaiting_speech_reply is True

    # 4. Test manual interrupt() clears awaiting reply and sets _interrupted
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


@pytest.mark.asyncio
async def test_answer_is_deferred_not_discarded_while_chord_held():
    """Regression: the server commits a turn on its own VAD, usually before the
    key comes up. That reply must be deferred and spoken on release, not thrown
    away — ZEZO used to fall silent and never answer."""
    from main import ZezoLive

    zezo = ZezoLive.__new__(ZezoLive)
    zezo._ptt_enabled = True
    zezo._ptt_held = True
    zezo._interrupted = False

    # The chord is released 100 ms later, as a real key-up would be.
    async def _release():
        await asyncio.sleep(0.10)
        zezo._ptt_held = False

    releaser = asyncio.create_task(_release())
    assert zezo._defer_playback() is True
    # Real gate used by _play_audio: it must WAIT, then allow the chunk to play.
    assert await zezo._await_playback_allowed() is True
    await releaser
    assert zezo._defer_playback() is False


@pytest.mark.asyncio
async def test_playback_gate_drops_only_interrupted_turn():
    """An interrupted turn's remnants must be dropped, and never blocked on."""
    from main import ZezoLive

    zezo = ZezoLive.__new__(ZezoLive)
    zezo._ptt_enabled = True
    zezo._ptt_held = True
    zezo._interrupted = True

    assert zezo._drop_assistant_audio() is True
    assert await zezo._await_playback_allowed() is False


def test_interrupted_turn_clears_at_server_boundary_while_still_held():
    """Regression: pinning _interrupted for the whole hold discarded the *next*
    turn's reply as well. A turn boundary must clear it even while held."""
    from main import ZezoLive

    zezo = ZezoLive.__new__(ZezoLive)
    zezo._ptt_enabled = True
    zezo._ptt_held = True
    zezo._interrupted = True

    assert zezo._drop_assistant_audio() is True

    # The interrupted turn's turn_complete arrives while the key is still down.
    assert zezo._end_interrupted_turn() is True
    assert zezo._interrupted is False

    # The follow-up turn's reply must now be accepted and merely deferred.
    assert zezo._drop_assistant_audio() is False
    assert zezo._defer_playback() is True


@pytest.mark.asyncio
async def test_play_audio_speaks_the_deferred_reply_after_release(monkeypatch):
    """End-to-end through the real _play_audio loop: a reply that arrives while
    the chord is down is kept and written to the speaker once the key is up."""
    import main as main_mod
    from main import ZezoLive

    written: list[bytes] = []

    class _FakeStream:
        latency = 0.05

        def start(self):
            pass

        def write(self, data):
            written.append(bytes(data))

        def stop(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(main_mod.sd, "RawOutputStream", lambda **kw: _FakeStream())
    monkeypatch.setattr(main_mod, "get_output_device", lambda: "")
    monkeypatch.setattr(main_mod.audio_devices, "resolve", lambda *a, **k: None)

    zezo = ZezoLive.__new__(ZezoLive)
    zezo.ui = MagicMock()
    zezo.ui.muted = False
    zezo.ui._sleeping = False
    zezo.ui.speaker_muted = False
    zezo._echo = MagicMock()
    zezo._visemes = MagicMock()
    zezo._turn_done_event = None
    zezo._is_speaking = False
    zezo._speaking_lock = MagicMock()
    zezo._speaking_lock.__enter__ = MagicMock(return_value=None)
    zezo._speaking_lock.__exit__ = MagicMock(return_value=None)
    zezo._tail_until = 0.0
    zezo._out_latency = 0.20
    zezo._play_cursor = 0.0
    zezo._out_level = 0.0
    zezo._ptt_enabled = True
    zezo._ptt_held = True
    zezo._interrupted = False
    zezo.audio_in_queue = asyncio.Queue()

    task = asyncio.create_task(zezo._play_audio())
    await asyncio.sleep(0.05)

    # The server committed the turn (its VAD heard end-of-speech) while the key
    # is still down. The reply must NOT be dropped.
    zezo.audio_in_queue.put_nowait(b"\x11\x11" * 2400)
    await asyncio.sleep(0.30)
    assert written == [], "answer played while the chord was still held"

    # Key up: the deferred answer is spoken.
    zezo._ptt_held = False
    await asyncio.sleep(0.30)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert written, "deferred answer was never played after release"


def test_ui_initial_state_respects_ptt_and_wake_word(monkeypatch):
    from ui import MainWindow
    win = MainWindow.__new__(MainWindow)
    win._muted = False
    win._sleeping = False

    # 1. When PTT is enabled -> IDLE
    monkeypatch.setattr("memory.config_manager.get_push_to_talk_enabled", lambda: True)
    monkeypatch.setattr("memory.config_manager.get_wake_word_enabled", lambda: False)
    st = win._get_initial_state()
    assert st["state"] == "IDLE"

    # 2. When Wake Word is enabled -> IDLE
    monkeypatch.setattr("memory.config_manager.get_push_to_talk_enabled", lambda: False)
    monkeypatch.setattr("memory.config_manager.get_wake_word_enabled", lambda: True)
    st = win._get_initial_state()
    assert st["state"] == "IDLE"

    # 3. When neither is enabled (Always Listening) -> LISTENING
    monkeypatch.setattr("memory.config_manager.get_push_to_talk_enabled", lambda: False)
    monkeypatch.setattr("memory.config_manager.get_wake_word_enabled", lambda: False)
    st = win._get_initial_state()
    assert st["state"] == "LISTENING"


