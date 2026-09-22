# Phonlab Desktop

Early-stage demo for the Phonlab GUI. Features audio playback, waveform and spectrogram visualization.

## Pull from Github

```
git clone https://github.com/alecmullen/phonlab-desktop.git
cd phonlab-desktop
```

## Environment Setup

We recommend using uv or conda to set up the environment.

### uv
```
uv sync
source .venv/bin/activate
```
  - *If on Windows*: replace `source .venv/bin/activate` with `.venv\Scripts\activate`

### conda

```
conda env create -f environment.yml
conda activate phonlab_desktop
```

### Without conda or uv
Make sure python 3.12 (>=3.12.10) is installed on your machine first (Use the [3.12.10 installer](https://www.python.org/downloads/release/python-31210/)).
```
python3.12 -m venv .venv
source .venv/bin/activate
pip install .
```
  - *If on Windows*: replace `source .venv/bin/activate` with `.venv\Scripts\activate`

## Running the GUI
From the project directory:
```
python src/phonlab_desktop.py
```
## Using the App
Once the app starts up, click on the popup card and select a `.wav` file from your computer to load. Once the audio is processed, you will see the waveform. Click 'Spectrogram' to see the spectrogram view along side it.

When opening the app, may select one `.TextGrid` along with the `.wav` file. Click 'Annotation' to see annotations imported from a `.TextGrid` file. Altenatively, you can drag and drop a `.TextGrid` file into the window. For now, only IntervalTiers will be read, and PointTiers will be ignored.

### Editing

Audio can be edited by copy and paste. Select a chunk of audio to copy or cut it, and set a mark before pasting it. Copying a clip will automatically open that clip in a separate tab. 

### Commands

 - **Click**: play the visible window
 - **Click + Drag**: select a chunk of waveform
 - **Double Click**: zoom in to the selected chunk
 - **Scroll**: pan/shift the location of the visible window in time
 - **Shift + Scroll**: zoom
 - **Shift + Click**: set mark
 - **Cmd + C**: copy selected audio
 - **Cmd + X**: cut selected audio
 - **Cmd + V**: paste audio from clipboard to set mark
 - **Cmd + S**: save audio
 - **Cmd + Scroll**:
    - On spectrogram: adjust the gray scale
    - On waveform: adjust the magnification
 - **Right Click**: see a context menu
 - **Up/Down Arrow Keys**: zoom
 - **Right/Left Arrow Keys**: pan

 ### Context Menu
  - Over any Plot:
    - **Resample**: open menu for resampling primary audio channel
    - **Set Mark**
    - **Remove Mark**
  - Spectrogram
    - **Spectrogram settings**: set sample rate, window size and step size for the spectrogram 
