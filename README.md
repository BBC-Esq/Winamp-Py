# Winamp-Py

<div align="center">

<img width="1414" height="313" alt="image" src="https://github.com/user-attachments/assets/5d8e4087-796e-4967-b7ef-888c64245e06" />

A Winamp-inspired media player built with Python, featuring real-time audio visualizations powered by OpenGL.

<img width="655" height="905" alt="image" src="https://github.com/user-attachments/assets/ec8fe236-c5f9-4d3a-987e-7927bb737a9e" />

</div>

## Features

- Play MP3, WAV, FLAC, OGG, and M4A files
- Drag-and-drop playlist with reordering
- Real-time OpenGL visualizations (Geiss-style) with 8 waveform modes and 8 color palettes
- Fullscreen visualization mode (double-click the visualizer)
- Customizable visualization settings (trails, glow, particles, colors)
- Volume control and seek bar
- Remembers window state, playlist, and settings between sessions

## Requirements

- Python 3.10+
- [VLC media player](https://www.videolan.org/vlc/) must be installed on your system

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/BBC-Esq/Winamp-Py.git
   cd Winamp-Py
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .
   Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run:
   ```
   python main.py
   ```

## Usage

- **Add music** - drag and drop files onto the playlist or use File > Open Files
- **Playback** - use the transport buttons or double-click a track
- **Reorder** - drag tracks within the playlist
- **Remove tracks** - right-click a track
- **Visualization** - select a visualization from the View menu; double-click it for fullscreen (Escape to exit)
- **Settings** - View > Visualization Settings to adjust trails, glow, colors, and effects
- **Volume** - use the slider or mouse wheel
