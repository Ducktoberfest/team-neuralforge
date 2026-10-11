"""Sound effects and audio engine for DuckTutor.

Synthesizes standalone WAV audio in pure Python without external dependencies.
Provides authentic rubber duck quacks, squeaks, and celebratory audio cues.
"""

from __future__ import annotations

import base64
import functools
import io
import math
import struct
import wave
from typing import Dict, Literal

import streamlit as st

SoundName = Literal["quack", "squeak", "curious", "success", "hint", "retry", "submit", "fanfare"]

AVAILABLE_SOUNDS = ("quack", "squeak", "curious", "success", "hint", "retry", "submit", "fanfare")

SOUND_ALIASES: Dict[str, str] = {
    "submit": "curious",
    "fanfare": "success",
}


@functools.lru_cache(maxsize=16)
def synthesize_wav(kind: SoundName = "quack", sample_rate: int = 22050) -> bytes:
    """Synthesize pure WAV audio bytes for rubber duck sound effects."""
    kind = SOUND_ALIASES.get(kind, kind)  # type: ignore
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = []

        if kind == "quack":
            # Classic rubber duck quack: downward pitch sweep with nasal formants and vocal flutter
            duration = 0.26
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                f0 = 380.0 - 160.0 * (t / duration)
                env = math.sin(math.pi * (t / duration) ** 0.8)
                flutter = 1.0 + 0.3 * math.sin(2 * math.pi * 26 * t)
                h1 = math.sin(2 * math.pi * f0 * t)
                h2 = 0.65 * math.sin(2 * math.pi * 2 * f0 * t)
                h3 = 0.45 * math.sin(2 * math.pi * 3 * f0 * t)
                formant = 0.7 * math.sin(2 * math.pi * 820 * t)
                s = (h1 + h2 + h3 + formant) * env * flutter * 0.25
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        elif kind == "squeak":
            # High-pitched rubber duck squeeze squeak
            duration = 0.16
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                f = 950 + 750 * math.sin(math.pi * (t / duration))
                env = math.sin(math.pi * (t / duration))
                s = (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(2 * math.pi * 2 * f * t)) * env * 0.4
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        elif kind == "curious":
            # Inquisitive rising pitch bend: 'Quack?'
            duration = 0.24
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                f0 = 280.0 + 160.0 * (t / duration) ** 1.3
                env = math.sin(math.pi * (t / duration) ** 0.9)
                flutter = 1.0 + 0.2 * math.sin(2 * math.pi * 22 * t)
                h1 = math.sin(2 * math.pi * f0 * t)
                h2 = 0.5 * math.sin(2 * math.pi * 2 * f0 * t)
                s = (h1 + h2) * env * flutter * 0.35
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        elif kind == "success":
            # Celebratory double quack + major chord fanfare
            duration = 0.45
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                if t < 0.14:
                    f = 523.25  # C5
                    env = math.sin(math.pi * (t / 0.14))
                    s = math.sin(2 * math.pi * f * t) * env * 0.35
                elif t < 0.28:
                    t2 = t - 0.14
                    f = 659.25  # E5
                    env = math.sin(math.pi * (t2 / 0.14))
                    s = math.sin(2 * math.pi * f * t2) * env * 0.4
                else:
                    t3 = t - 0.28
                    env = math.exp(-t3 * 7.0)
                    c = math.sin(2 * math.pi * 783.99 * t3)  # G5
                    e = 0.5 * math.sin(2 * math.pi * 1046.50 * t3)  # C6
                    s = (c + e) * env * 0.4
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        elif kind == "hint":
            # Thoughtful, gentle warm quack
            duration = 0.22
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                f = 320 - 60 * (t / duration)
                env = math.sin(math.pi * (t / duration))
                s = (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * 2 * f * t)) * env * 0.3
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        elif kind == "retry":
            # Sympathetic descending quack
            duration = 0.26
            n = int(duration * sample_rate)
            for i in range(n):
                t = i / sample_rate
                f = 270 - 70 * (t / duration)
                env = math.sin(math.pi * (t / duration))
                flutter = 1.0 + 0.3 * math.sin(2 * math.pi * 18 * t)
                s = (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(2 * math.pi * 2 * f * t)) * env * flutter * 0.3
                frames.append(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000)))

        else:
            raise ValueError(f"Unknown sound kind: {kind}")

        wf.writeframes(b"".join(frames))
    return buf.getvalue()


@functools.lru_cache(maxsize=16)
def get_sound_data_uri(kind: SoundName = "quack") -> str:
    """Return an RFC 2397 base64 data URI for the synthesized audio."""
    raw = synthesize_wav(kind)
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:audio/wav;base64,{b64}"


def queue_sound(kind: SoundName) -> None:
    """Queue a sound to be played on the next Streamlit rendering cycle."""
    actual_kind = SOUND_ALIASES.get(kind, kind)
    if actual_kind not in AVAILABLE_SOUNDS:
        return
    st.session_state["_pending_sound"] = actual_kind


def play_sound(kind: SoundName) -> None:
    """Queue a sound effect for playback (convenience alias)."""
    queue_sound(kind)


def play_sound_immediate(kind: SoundName) -> None:
    """Render an audio tag directly if audio is enabled."""
    if not st.session_state.get("duck_audio_enabled", True):
        return
    uri = get_sound_data_uri(kind)
    st.markdown(
        f'<audio autoplay style="display:none;" src="{uri}"></audio>',
        unsafe_allow_html=True,
    )


def render_pending_sound() -> None:
    """Check for queued sound and render it if audio is enabled."""
    sound = st.session_state.pop("_pending_sound", None)
    if not sound:
        return
    if not st.session_state.get("duck_audio_enabled", True):
        return
    uri = get_sound_data_uri(sound)
    st.markdown(
        f'<audio autoplay style="display:none;" src="{uri}"></audio>',
        unsafe_allow_html=True,
    )


def render_audio_sidebar() -> None:
    """Render the Duck Audio controls in the Streamlit sidebar."""
    with st.expander("🦆 Duck Audio & Quacks", expanded=False):
        st.caption("Pure offline synthesized sound effects for learning events.")
        enabled = st.checkbox("Enable duck sound effects", value=True, key="duck_audio_enabled")
        if enabled:
            if st.button("🦆 Squeeze the Duck!", key="squeeze_duck_btn", use_container_width=True):
                queue_sound("squeak")
                st.rerun()
            st.caption("Sounds trigger on predictions, hints, and verified solutions.")
