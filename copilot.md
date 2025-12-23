# Keyboard MIDI LEDs Project - AI Agent Documentation

## Project Overview

This project is a Python-based desktop application that controls an LED strip mounted on a piano keyboard via an Arduino Nano. It visualizes MIDI files in real-time by lighting up corresponding keys on the LED strip, helping piano learners with finger placement and sight reading.

### Key Components

1. **Desktop Application** (Python/Pygame)
   - MIDI file parser
   - Real-time playback engine
   - LED visualization and control
   - Serial communication with Arduino
   - Configuration mode for LED mapping

2. **Arduino Nano Firmware** (C++)
   - Controls WS2811/WS2812 LED strip (123 LEDs)
   - Receives commands via high-speed serial (2Mbps)
   - Manages LED brightness and color for 72 piano keys
   - Supports configurable LED-to-key mapping

---

## Architecture

### Communication Protocol

The desktop application and Arduino communicate via serial using a packet-based protocol:

#### Packet Structure
```
[PACKET_START] [COUNT] [DATA...] [PACKET_END]
```

- `PACKET_START`: `0xAA` - Packet start marker
- `COUNT`: Number of data triplets (1-72)
- `DATA`: Triplets of `[FLAG, KEY/INDEX, VALUE]`
- `PACKET_END`: `0x55` - Packet end marker

#### Flags
- `UPDATE_FLAG (0x01)`: Update key brightness
  - Format: `[0x01, key_number, brightness_0_to_99]`
  
- `CLEAR_FLAG (0x02)`: Clear all LEDs
  - Format: `[0x02, 0, 0]` (single triplet)
  
- `CONFIG_FLAG (0x03)`: Configure LED mapping
  - Format: 9 triplets of `[0x03, byte_index, byte_value]`
  - Used to send LED configuration (which keys use 3 LEDs vs 2 LEDs)

#### Response Flags
- `READY_FLAG (0xCC)`: Command executed successfully
- `ERROR_FLAG (0xEE)`: Command failed or invalid packet

### LED Mapping System

The Arduino maps 72 piano keys to 123 LEDs on the strip:

- **Standard Keys**: Use 2 LEDs each
- **3-LED Keys**: Use 3 LEDs (configurable via configuration mode)
  - Purpose: Shift alignment to match physical keyboard differences
  - Configuration stored in 9-byte bit array (72 keys / 8 bits = 9 bytes)

#### LED Color Pattern (White vs Black Keys)
- White keys (even): Green `(0, brightness, 0)`
- White keys (odd): Yellow `(brightness, brightness, 0)`
- Black keys: Red `(brightness, 0, 0)`

The pattern repeats for each octave: `[W, B, W, B, W, W, B, W, B, W, B, W]`
Where W=white (0), B=black (1)

---

## File Structure

### Desktop Application (`/DesktopApplication`)

#### Core Files

**`MAIN.py`**
- Entry point with crash recovery
- Restarts app on errors while preserving state

**`Config.py`**
- Global configuration constants
- Serial settings (port, baud rate)
- Display settings (window size, colors)
- Protocol constants (flags, packet markers)

**`LED_Config.py`**
- Manages LED mapping configuration
- Saves/loads configuration from `led_config.json`
- Generates config bytes for Arduino
- API:
  - `set_three_led_key(key, enabled)`: Set 3-LED status for a key
  - `is_three_led_key(key)`: Check if key uses 3 LEDs
  - `toggle_three_led_key(key)`: Toggle 3-LED status
  - `get_config_bytes()`: Get 9-byte config for Arduino

**`Serial.py`**
- Serial communication wrapper
- Methods:
  - `connect()`: Connect to Arduino
  - `send_keys(key_brightness_dict)`: Send key updates
  - `send_clear()`: Clear all LEDs
  - `send_config(config_bytes)`: Send LED configuration

**`MIDI_Parser.py`**
- Parses MIDI files using `mido` library
- Returns: `(note_times, midi_length)`
  - `note_times`: Array of `[(start_time, end_time)]` for each key
  - `midi_length`: Total duration in seconds

#### GUI Files (`/DesktopApplication/GUI`)

**`Main_Window.py`**
- Main application GUI (Pygame-based)
- Features:
  - MIDI file selection and playback
  - Speed control (0.25x to 3.0x, custom speeds)
  - Playhead slider for seeking
  - Skip forward/backward by chord
  - Configuration mode for LED mapping
- Key methods:
  - `toggle_config_mode()`: Enter/exit configuration mode
  - `_handle_config_mode_click(key)`: Handle key clicks in config mode
  - `send_config(config_bytes)`: Send configuration to Arduino

**`Visuals.py`**
- Pygame UI components:
  - `SimpleButton`: Clickable buttons
  - `SimpleDropdown`: Dropdown menus
  - `SimpleSlider`: Draggable sliders
  - `SimpleKeyboard`: Visual keyboard display
- `SimpleKeyboard` methods:
  - `set_active(key_brightness_dict)`: Set key brightness
  - `set_falling_notes(notes)`: Set falling note animations
  - `get_clicked_key(mouse_pos)`: Detect key clicks
  - `draw(surf)`: Render keyboard

### Arduino Firmware (`/ArduinoNano`)

**`ArduinoNano.ino`**
- Main firmware for Arduino Nano
- Controls Adafruit NeoPixel strip (WS2811/WS2812)
- Key functions:
  - `renderLEDs()`: Map keys to LEDs and update strip
  - `isThreeLEDKey(key)`: Check if key uses 3 LEDs
  - `clearAllKeys()`: Turn off all LEDs
  - `checkAndTimeoutKeys()`: Auto-fade unused LEDs after 200ms
- Global state:
  - `keyBrightness[72]`: Current brightness for each key (0-99)
  - `threeLEDKeys[9]`: Bit array of 3-LED key configuration
  - `keyLastUpdate[72]`: Last update timestamp for auto-timeout

---

## Configuration Mode

### Purpose
Allows users to customize which keys use 3 LEDs instead of 2, enabling the LED strip to align properly with different physical keyboards.

### How It Works

1. **Entering Configuration Mode**
   - Click "Configure" button in GUI
   - All LEDs turn on at full brightness
   - Orange banner appears with instructions
   - Playback automatically stops

2. **Selecting 3-LED Keys**
   - Click on any key in the keyboard visualization
   - Key toggles between 2-LED (default) and 3-LED mode
   - 3-LED keys show green overlay
   - Changes are temporary until saved

3. **Saving Configuration**
   - Click "Configure" button again to exit and save
   - Configuration saved to `led_config.json`
   - Configuration sent to Arduino via serial
   - Arduino updates LED mapping in real-time

### Configuration File Format

`led_config.json`:
```json
{
  "three_led_keys": [11, 17, 36]
}
```

Array contains key numbers (0-71) that should use 3 LEDs.

---

## Building and Running

### Desktop Application

#### Prerequisites
```bash
pip install pygame mido python-rtmidi pyserial
```

#### Running
```bash
cd DesktopApplication
python MAIN.py
```

#### Configuration
Edit `Config.py` to set:
- `SERIAL_PORT`: COM port (e.g., 'COM9' on Windows, '/dev/ttyUSB0' on Linux)
- `BAUD_RATE`: Keep at 2000000 (matches Arduino)

### Arduino Firmware

#### Prerequisites
- Arduino IDE with Adafruit NeoPixel library
- Arduino Nano board

#### Flashing
1. Open `ArduinoNano.ino` in Arduino IDE
2. Select board: Tools > Board > Arduino Nano
3. Select processor: Tools > Processor > ATmega328P (Old Bootloader)
4. Select port: Tools > Port > (your Arduino port)
5. Click Upload

#### Hardware Setup
- LED strip data pin: Digital pin 11
- LED strip power: External 5V power supply (LEDs draw significant current)
- Arduino power: USB from computer

---

## Development Notes

### Adding New Features

#### Adding a New Serial Command

1. **Define flag in `Config.py`**:
```python
NEW_FLAG = 0x04
```

2. **Add to Arduino firmware**:
```cpp
#define NEW_FLAG 0x04
```

3. **Implement handler in Arduino `loop()`**:
```cpp
else if (flag == NEW_FLAG && count == expected_count) {
  // Handle command
}
```

4. **Add desktop method in `Serial.py` or `Main_Window.py`**:
```python
def send_new_command(self, data):
    frame = bytearray([PACKET_START, count])
    # Add triplets
    frame.append(PACKET_END)
    # Send and wait for response
```

#### Modifying LED Rendering

Edit `renderLEDs()` in `ArduinoNano.ino`. Key considerations:
- Loop processes keys 0-71 sequentially
- LED index advances by 2 or 3 based on `isThreeLEDKey(key)`
- First 4 LEDs are skipped (LED index starts at 4)
- Total LED count: 123 (LED_COUNT)

### Common Issues

**LEDs not responding:**
- Check serial connection (correct port in Config.py)
- Verify baud rate matches (2000000)
- Check power supply to LED strip

**Wrong keys lighting up:**
- LED mapping may need adjustment via configuration mode
- Verify `MIDI_KEY_OFFSET` (default 36 = C2)

**Performance issues:**
- Reduce `MAX_BRIGHTNESS` in Config.py
- Increase `UPDATE_RATE` (reduces update frequency)
- Use slower playback speed

### Testing

#### Manual Testing Checklist
- [ ] MIDI file loads successfully
- [ ] Play/pause works correctly
- [ ] Speed changes apply smoothly
- [ ] Seeking with slider works
- [ ] Skip forward/back navigates correctly
- [ ] Configuration mode activates/deactivates
- [ ] Key clicks in config mode toggle 3-LED status
- [ ] Configuration persists across restarts
- [ ] LEDs match keyboard visualization

#### Serial Communication Testing
```python
# Test in Python REPL
from Serial import KeyboardController
kb = KeyboardController()
kb.connect()
kb.send_keys({0: 99, 12: 99, 24: 99})  # Light up C keys
kb.send_clear()  # Clear all
kb.disconnect()
```

---

## Future Enhancements

### Suggested Improvements
- [ ] Multi-track MIDI support
- [ ] Real-time MIDI keyboard input
- [ ] Customizable color schemes
- [ ] Learning mode with pause on wrong notes
- [ ] Performance optimizations for faster playback
- [ ] Linux/Mac compatibility testing
- [ ] 3D-printed keyboard mount designs

### Known Limitations
- Maximum playback speed: ~0.5x (hardware limitation)
- No MIDI keyboard input support yet
- Windows-focused (paths, COM ports)
- Limited to 72 keys (6 octaves)

---

## Troubleshooting

### Serial Connection Issues

**"Serial connection error" on startup:**
1. Check Arduino is connected and recognized by OS
2. Update `SERIAL_PORT` in Config.py
3. Close other programs using the serial port
4. Try unplugging and reconnecting Arduino

### LED Issues

**LEDs show wrong colors:**
- Check LED strip type (NEO_GRB vs NEO_RGB in Arduino code)
- Verify power supply voltage (5V for WS2811/WS2812)

**LEDs are too dim/bright:**
- Adjust `BRIGHTNESS` in ArduinoNano.ino (0-255)
- Adjust `MAX_BRIGHTNESS` in Config.py (affects fade range)

**Some LEDs don't light up:**
- Check LED strip isn't damaged
- Verify LED_COUNT matches actual strip length
- Check data line connection

### MIDI Playback Issues

**Notes don't align with music:**
- Adjust `MIDI_KEY_OFFSET` in Config.py
- Check MIDI file is properly formatted

**Playback is choppy:**
- Reduce visual effects (falling notes)
- Lower FPS in Config.py
- Close other CPU-intensive programs

---

## Code Style and Conventions

### Python Code
- Use 4 spaces for indentation
- Follow PEP 8 naming conventions
- Add docstrings to public methods
- Keep functions focused and single-purpose

### Arduino Code
- Use camelCase for variables and functions
- Constants in UPPER_CASE
- Add comments for complex logic
- Keep loop() efficient (no blocking delays)

### Git Workflow
- Create feature branches for new features
- Write descriptive commit messages
- Test changes before committing
- Keep commits focused and atomic

---

## Resources

### Libraries Used
- **Pygame**: GUI and graphics (https://www.pygame.org/)
- **mido**: MIDI file parsing (https://mido.readthedocs.io/)
- **pyserial**: Serial communication (https://pyserial.readthedocs.io/)
- **Adafruit NeoPixel**: LED control (https://github.com/adafruit/Adafruit_NeoPixel)

### References
- MIDI specification: https://www.midi.org/specifications
- WS2812 LED protocol: https://cdn-shop.adafruit.com/datasheets/WS2812.pdf
- Arduino Serial reference: https://www.arduino.cc/reference/en/language/functions/communication/serial/

---

## License and Credits

This is an open-source educational project designed to help piano learners visualize music through LED feedback.

**Author**: SandDew
**Repository**: https://github.com/SandDew/KeyboardMidiLEDs-

---

## Quick Reference

### Key Numbers (MIDI)
- Key 0: C2 (MIDI note 36)
- Key 12: C3 (MIDI note 48)
- Key 24: C4 (Middle C, MIDI note 60)
- Key 36: C5 (MIDI note 72)
- Key 48: C6 (MIDI note 84)
- Key 60: C7 (MIDI note 96)
- Key 71: B7 (MIDI note 107)

### Serial Protocol Quick Reference
```
Update keys:  [0xAA] [N] [0x01, key, brightness] * N [0x55]
Clear all:    [0xAA] [1] [0x02, 0, 0] [0x55]
Configure:    [0xAA] [9] [0x03, idx, val] * 9 [0x55]
Response:     [0xCC] success or [0xEE] error
```

### File Paths
- Config: `DesktopApplication/led_config.json`
- Main entry: `DesktopApplication/MAIN.py`
- Arduino: `ArduinoNano/ArduinoNano.ino`
- MIDI files: `MIDI_Files/` (not tracked in git)
