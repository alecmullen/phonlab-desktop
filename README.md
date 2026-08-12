# Phonlab Desktop

Early-stage demo for the Phonlab GUI. Features audio playback, waveform and spectrogram visualization.

## Pull from Github

```
git clone https://github.com/alecmullen/phonlab-desktop.git
cd phonlab-desktop
```

## Environment Setup

We recommend using conda or uv to set up the environment.

### conda

```
conda env create -f environment.yml
conda activate phonlab_desktop
```
### uv
```
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```
For Windows, replace `source .venv/bin/activate` with `.venv\Scripts\activate`
### venv + pip
Make sure python 3.12 is installed on your machine first (Use the [3.12.10 installer](https://www.python.org/downloads/release/python-31210/)).
```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
For Windows, replace `source .venv/bin/activate` with `.venv\Scripts\activate`

## Running the GUI
From the project directory:
```
python src/phonlab_desktop.py
```
## Using the App
When the app loads, click on the white tool card and select a `.wav` file from your computer to load. Once the audio is processed, you will see the waveform. Click 'Spectrogram' to see the spectrogram view along side it.

### Commands

 - **Click**: play the visible window
 - **Click + Drag**: select a chunk of waveform
 - **Double Click**: zoom in to the selected chunk
 - **Scroll**: pan/shift the location of the visible window in time
 - **Shift + Scroll**: zoom
 - **Cmd + Scroll**:
    - On spectrogram: adjust the gray scale
    - On waveform: adjust the magnification
 - **Right Click**: see a context menu
 - **Up/Down Arrow Keys**: zoom
 - **Right/Left Arrow Keys**: pan
