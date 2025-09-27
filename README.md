# MIDI LEDs-

## About

This is a Python application designed to help piano learners by providing a visual representation of key presses using an LED strip mounted on the keyboard. It aids with finger placement and sight reading of sheet music. Do keep in mind that this project is far from polished, cannot handle faster MIDI files, and has a number of errors. 
Additionally, the script is designed for Windows. A Linux or Mac could work, but the code doesn't currently accommodate it.

## Setup 
- Flash an Arduino Nano with the sketch in the 'Arduino' folder.
- Plug in an LED strip to the top of the nano for a serial -- I recommend buying a WS2811 strip with a three-pronged connector at the end. That way, you won't have to solder anything.
- Install dependencies.
- Launch 'MAIN.py'
- Select your MIDI file, play, and ideally, it'll just work from there.

---

## Gallery

<div align="center">
  <img src="1.jpg" alt="Keyboard with MIDI LEDs active" width="400" style="margin:10px;">
  <img src="2.jpg" alt="Close-up of LED strip on keys" width="400" style="margin:10px;">
</div>

---

## Roadmap

- [ ] Improve LED responsiveness to handle more than 0.25x speed. 
- [ ] Make CAD files for 3D printable parts / Laser cut wood (so I won't have to tape the LEDs to my keyboard)
- [ ] Add MIDI Keyboard support
- [ ] Once optimized, make a 'learning' mode. 
