import pygame

# Serial communication settings
SERIAL_PORT = 'COM9'
BAUD_RATE = 2000000
PACKET_START = 0xAA
PACKET_END = 0x55
UPDATE_FLAG = 0x01
READY_FLAG = 0xCC
ERROR_FLAG = 0xEE
CONFIG_FLAG = 0x03  # New: send LED configuration

# MIDI settings
MIDI_KEY_OFFSET = 36
NUM_KEYS = 72  # 6 octaves

# Display settings
WINDOW_WIDTH = 1240
WINDOW_HEIGHT = 720
VISUALIZATION_HEIGHT = 400
KEYBOARD_HEIGHT = 120
DROPDOWN_OFFSET = 20  # Pixels below slider for dropdown menu

# Performance settings
FPS = 60
FALL_TIME_VISIBLE = 2.0  # How long before a note plays that it starts falling
MAX_FALLING_NOTES = 1000
NOTE_CLEANUP_INTERVAL = 0.5

# Key settings (LED brightness and fading)
FADE_RANGE = 0.8  # Fade range in seconds for better visibility
MAX_BRIGHTNESS = 85  # Maximum LED brightness (0-255 scale for GUI, converted to 0-99 for Arduino)
UPDATE_RATE = 0.01   # Update rate in seconds

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

# Button colors
BUTTON_COLOR = (70, 70, 70)
BUTTON_HOVER = (90, 90, 90)
BUTTON_PRESSED = (50, 50, 50)

# Configuration mode colors
CONFIG_MODE_OVERLAY = (255, 165, 0, 100)  # Orange overlay for config mode
CONFIG_MODE_SELECTED = (0, 255, 0, 150)   # Green for selected 3-LED keys