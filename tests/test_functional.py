from shutil import rmtree

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from weighslide import run_weighslide


def test_function():
    plt.rcParams["savefig.dpi"] = 120
    df = pd.DataFrame()
    df['wave'] = [1, 1, 1, 3, 3, 3] * 8
    df["random"] = np.random.random_sample(df.shape[0])
    df["noisy wave"] = df.wave + df.random * 5
    fig, ax = plt.subplots()
    df.plot(title="input data: noisy wave", ax=ax)
    weighslide_dir = Path(__file__).parents[1]
    temp_output_dir = weighslide_dir / "tests/temp_output"
    if not temp_output_dir.is_dir():
        temp_output_dir.mkdir(parents=True)
    data_csv = temp_output_dir / "wave.csv"
    df.to_csv(data_csv)

    # run weighslide with a window that averages every 6th position
    window = "9xxxxx9xxxxx9xxxxx9xxxxx9xxxxx9xxxxx9"
    run_weighslide(data_csv, window, "mean", name="wavetest", column="noisy wave", overwrite=True)

    weighslide_output_dir = temp_output_dir / "weighslide_output"
    assert (weighslide_output_dir / "wavetest9xxxxx9xxxxx9xxxxx9x.png").is_file()
    assert (weighslide_output_dir / "wavetest9xxxxx9xxxxx9xxxxx9x.xlsx").is_file()
    assert (weighslide_output_dir / "wavetest9xxxxx9xxxxx9xxxxx9x_mean.csv").is_file()
    assert (weighslide_output_dir / "wavetest9xxxxx9xxxxx9xxxxx9x_sliced.csv").is_file()

    if temp_output_dir.is_dir():
        rmtree(temp_output_dir)
