"""Beeps on the host's audio output for the simulation (HW-062).

A beep pattern becomes a 1000 Hz tone as WAV data and is played by the first available player: `paplay`,
`aplay` or `afplay`, or `winsound` on Windows. Playing never blocks the caller. Without a player, beeps are
only logged by the simulation.
"""

import functools
import io
import logging
import math
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from collections.abc import Callable
from pathlib import Path

from brewberrypi.hal import BeepPattern

log = logging.getLogger(__name__)

TONE_HZ = 1000
SAMPLE_RATE = 8000

Player = Callable[[bytes], None]
"""Plays WAV data; must not block."""


def pattern_wav(pattern: BeepPattern) -> bytes:
    """The pattern as 8-bit mono WAV: a 1000 Hz sine wave while on, silence while off."""
    samples = bytearray()
    for on, milliseconds in pattern:
        count = SAMPLE_RATE * milliseconds // 1000
        if on:
            start = len(samples)
            samples.extend(
                128 + round(100 * math.sin(2 * math.pi * TONE_HZ * (start + i) / SAMPLE_RATE))
                for i in range(count)
            )
        else:
            samples.extend(b"\x80" * count)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(samples))
    return buffer.getvalue()


def find_player() -> Player | None:
    """The first available audio player, or `None`."""
    if sys.platform == "win32":
        return _in_background(_play_winsound)
    for name, arguments in (("paplay", []), ("aplay", ["-q", "-"])):
        executable = shutil.which(name)
        if executable is not None:
            return _in_background(functools.partial(_play_stdin, [executable, *arguments]))
    afplay = shutil.which("afplay")
    if afplay is not None:
        return _in_background(functools.partial(_play_file, afplay))
    return None


def _in_background(play: Player) -> Player:
    def start(wav: bytes) -> None:
        threading.Thread(target=_guarded, args=(play, wav), name="beep", daemon=True).start()

    return start


def _guarded(play: Player, wav: bytes) -> None:
    try:
        play(wav)
    except Exception as error:  # a broken audio setup must never disturb the brewing
        log.debug("playing a beep failed: %s", error)


def _play_stdin(command: list[str], wav: bytes) -> None:
    subprocess.run(
        command, input=wav, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False
    )


def _play_file(afplay: str, wav: bytes) -> None:
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "beep.wav"
        file.write_bytes(wav)
        subprocess.run(
            [afplay, str(file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False
        )


def _play_winsound(wav: bytes) -> None:
    if sys.platform == "win32":
        import winsound  # noqa: PLC0415  (Windows only)

        winsound.PlaySound(wav, winsound.SND_MEMORY)
