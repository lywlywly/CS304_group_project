"""Plot log Mel spectrum and Mel Cepstrum of all speech files in `recordings/`.
Run as `python3 -m speech.project2.main`."""

import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from speech.project2.lib import (
    lifting,
    mfcc_homebrew,
    plot_cepstra,
    plot_log_mel_spectra,
)

from ..project1 import open_wave_file

plt.rcParams["font.size"] = 24

NUMBERS = (
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)

NS_FILTER_BANKS = (40, 30, 25)


def plot_audio_file(number: str, i: int, n_filter_banks: int):
    file_name = f"recordings/{number}{i}.wav"
    with open_wave_file(file_name, "rb") as wave_file:
        n_frames = wave_file.getnframes()
        frames = wave_file.readframes(n_frames)
    audio_array = np.frombuffer(frames, dtype=np.int16)
    assert len(audio_array) == n_frames

    cep, mspec, mel_frequencies = mfcc_homebrew(audio_array=audio_array)
    try:
        os.mkdir(f"log_spectra{n_filter_banks}")
    except:
        pass
    log_spec_file_name = f"log_spectra{n_filter_banks}/{number}{i}.png"
    log_spec_fig: Figure = plot_log_mel_spectra(mspec)
    # TODO: Generate `log_spec_fig`.
    log_spec_fig.savefig(log_spec_file_name, bbox_inches="tight")

    try:
        os.mkdir(f"cepstra{n_filter_banks}")
    except:
        pass
    ceps_file_name = f"cepstra{n_filter_banks}/{number}{i}.png"
    ceps_fig: Figure = plot_cepstra(lifting(cep))
    # TODO: Generate `ceps_fig`.
    ceps_fig.savefig(ceps_file_name, bbox_inches="tight")


def main():
    for number in NUMBERS:
        for i in range(4):
            for n_filter_banks in NS_FILTER_BANKS:
                plot_audio_file(number, i, n_filter_banks)


main() if __name__ == "__main__" else None
