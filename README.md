# Project TIO

Project TIO is a Windows desktop icon selection overlay written in Python.

The project started as a simple frame around desktop icons and gradually evolved into a smooth animated, rotating and audio-reactive interface.

## Features

- Detects desktop icons
- Finds the nearest icon to the mouse cursor
- Draws a transparent selection frame
- Opens selected icons with double click
- Smoothly moves and morphs the frame
- Rotates around the cursor
- Rainbow color animation
- Click pulse effect
- Audio-reactive size and thickness
- Bass detection using WASAPI loopback

## Versions

### v1_basic.py
The first version of the project.

- Basic desktop icon detection
- Simple rectangular selection frame
- Shift activation
- Opens selected icons

### v2_color_arrow.py
Adds visual effects.

- Rainbow colors
- Animated arrow
- Distance-based animation

### v3_smooth_animation.py
Major animation update.

- Rotating square around the mouse cursor
- NumPy-based point calculations
- Smooth transition between cursor and icon
- Polygon frame instead of a simple rectangle

### v4_audio_reactive.py
Current version.

- Rainbow animated frame
- Click pulse effect
- WASAPI loopback audio capture
- Frame reacts to system audio
- Bass frequency detection
- Automatic audio reconnect
- Error handling for Windows and audio devices

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt