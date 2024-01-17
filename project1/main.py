import wave
from contextlib import contextmanager
from enum import Enum
from queue import Queue
from typing import Mapping

import numpy as np
from numpy.typing import NDArray
from pyaudio import PyAudio, paContinue, paInt16

RESOLUTION_FORMAT = paInt16
"""Bit resolution per frame."""
SIZEOF_FRAME = 2
"""Size of each frame in bytes."""
N_CHANNEL = 1
"""Number of audio channels."""
SAMPLING_RATE = 16000
"""Audio sampling rate in frames per second."""
CHUNK_MS = 20
"""Audio sample chunk duration in milliseconds."""
N_FRAME_PER_CHUNK = SAMPLING_RATE * CHUNK_MS // 1000
"""Number of frames per audio sample chunk."""
MAX_PAUSE_MS = 2000
"""Maximum pause duration in milliseconds during speech."""


def main(out_file_name="output.wav"):
    """Record 5sec into `output.wav`"""
    audio_queue: Queue[tuple[bytes, int]] = Queue()
    stream_callback = get_stream_callback(audio_queue)

    buffer = b""
    buffer_size = SAMPLING_RATE * MAX_PAUSE_MS * SIZEOF_FRAME // 1000

    with wave.open(out_file_name, "wb") as out_file, open_pyaudio() as py_audio:
        # Configure output file.
        out_file.setnchannels(N_CHANNEL)
        out_file.setsampwidth(py_audio.get_sample_size(RESOLUTION_FORMAT))
        out_file.setframerate(SAMPLING_RATE)

        stream = py_audio.open(
            format=RESOLUTION_FORMAT,
            channels=N_CHANNEL,
            rate=SAMPLING_RATE,
            input=True,
            frames_per_buffer=N_FRAME_PER_CHUNK,
            stream_callback=stream_callback,
        )

        input("Press Enter to start recording...")
        discard_first_at_least(audio_queue)
        print("Recording...")

        classify_sample = get_classify_sample()
        recording_status = get_recording_status()
        while True:
            data, _ = audio_queue.get(timeout=0.1)

            audio_array = np.frombuffer(data, dtype=np.int16)
            is_speech = classify_sample(audio_array)
            status = recording_status(is_speech)
            match status:
                case RecordingStatus.PENDING:
                    continue
                case RecordingStatus.GOING:
                    buffer += data
                    if len(buffer) > buffer_size:
                        out_file.writeframes(buffer[:-buffer_size])
                        buffer = buffer[-buffer_size:]
                case RecordingStatus.STOPPING:
                    break
        print("Stopping recording.")
        stream.close()


def get_stream_callback(audio_queue: Queue[tuple[bytes, int]]):
    """Get a callback for `PyAudio.open`, which sends input audio data to
    `audio_queue`."""

    def stream_callback(
        in_data: bytes | None,
        n_frame: int,
        time_info: Mapping[str, float],  # pyright: ignore reportUnusedVariable
        status: int,  # pyright: ignore reportUnusedVariable
    ):
        nonlocal audio_queue

        assert in_data is not None
        audio_queue.put((in_data, n_frame))
        return None, paContinue

    return stream_callback


def discard_first_at_least(audio_queue: Queue[tuple[bytes, int]], n_discard=5):
    """Discard first `n_discard` samples in `audio_queue` to avoid initial
    unstable samples. Then, discard all previous samples."""
    if audio_queue.qsize() < n_discard:
        for _ in range(n_discard):
            audio_queue.get(timeout=0.1)
    with audio_queue.mutex:
        audio_queue.queue.clear()


STARTING_THRESHOLD_DB = 15.0
"""Threshold from background in decibels for starting to classify as speeches."""
CONTINUING_THRESHOLD_DB = 2.0
"""Threshold from background in decibels for continuing to classify as speeches."""
STOPPING_THRESHOLD_DB = -20.0
"""Threshold from foreground in decibels for stopping to classify as speeches."""
WEAK_ADJUSTMENT = 0.05
STRONG_ADJUSTMENT = 0.8


def get_recording_status():
    """Get a closure that determines the current recording status based on
    whether a sample is classified as speech.
    Stopping condition: `MAX_PAUSE_MS` ms after speech stops.
    """
    off_time = 0
    started = False

    def recording_status(is_speech: bool) -> RecordingStatus:
        nonlocal off_time, started

        if not started:
            if is_speech:
                started = True
                return RecordingStatus.GOING
            return RecordingStatus.PENDING
        else:
            if is_speech:
                off_time = 0
            else:
                off_time += CHUNK_MS
        if off_time > MAX_PAUSE_MS:
            return RecordingStatus.STOPPING

        return RecordingStatus.GOING

    return recording_status


class RecordingStatus(Enum):
    """- `PENDING`: The recording has not started yet.
    - `GOING`: The recording is currently in progress.
    - `STOPPING`: The recording has been completed and should be stopped."""

    PENDING = -1
    GOING = 0
    STOPPING = 1


FORGET_FACTOR = 1.2
"""Forgetting factor for updating `level` energy in `get_classify_sample`."""


def get_classify_sample():
    """Get a closure that classifies whether each sample is speech.
    Speech is considered to start when the `level` energy is at least
    `STARTING_THRESHOLD_DB` higher than `background` energy;
    speech is considered to continue when the `level` energy is
    at least `CONTINUING_THRESHOLD_DB` higher than `background` energy and
    at least `STOPPING_THRESHOLD_DB` higher than `foreground` energy."""
    level: np.float64 | None = None
    background: np.float64 | None = None
    foreground = 0.0
    speaking = False

    def classify_frame(arr: NDArray[np.int16]) -> bool:
        nonlocal level, background, foreground, speaking
        current = sample_decibel_energy(arr)
        if level is None:
            level = current
        if background is None:
            background = current

        level = ((level * FORGET_FACTOR) + current) / (FORGET_FACTOR + 1.0)

        print(
            f"speaking: {'Y' if speaking else 'N'}, current: {current:.1f}, bg: {background:.1f}, fg: {foreground:.1f}, level: {level:.1f}."
        )

        if speaking:
            if (
                level - background < CONTINUING_THRESHOLD_DB
                or level - foreground < STOPPING_THRESHOLD_DB
            ):
                speaking = False
                background = background if background < level else level
            else:
                foreground = adjust_conditionally_on_change(
                    foreground, level, STRONG_ADJUSTMENT, WEAK_ADJUSTMENT
                )
        if not speaking:
            if level - background >= STARTING_THRESHOLD_DB:
                speaking = True
                foreground = level
            else:
                background = adjust_conditionally_on_change(
                    background, level, WEAK_ADJUSTMENT, STRONG_ADJUSTMENT
                )

        return speaking

    return classify_frame


def adjust_conditionally_on_change(
    original, updated, adjustment_if_inc, adjustment_if_dec
):
    """Adjust `original` based on whether `updated` increased from it."""
    diff = updated - original
    return (adjustment_if_inc if diff > 0 else adjustment_if_dec) * diff + original


def sample_decibel_energy(arr: NDArray[np.int16]) -> np.float64:
    """Calculate the energy of an audio sample in decibel."""
    arr = arr.astype(np.int64)  # avoid overflow
    power = arr.dot(arr) / arr.size
    return np.log10(power) * 10.0


@contextmanager
def open_pyaudio():
    """Provide a self-cleaning-up `PyAudio` instance for a `with` statement."""
    py_audio = None
    try:
        yield (py_audio := PyAudio())
    finally:
        py_audio.terminate() if py_audio else None


main() if __name__ == "__main__" else None
