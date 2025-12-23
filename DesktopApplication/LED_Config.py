"""
LED Configuration Manager
Handles saving and loading LED mapping configuration for the keyboard.
"""
import json
import os

CONFIG_FILE = "led_config.json"

class LEDConfigManager:
    def __init__(self):
        # Default configuration: keys that use 3 LEDs for alignment
        # By default, matches the old hardcoded 1-LED keys (which shift to be 3-LED in new system)
        self.three_led_keys = set()
        self.load_config()
    
    def load_config(self):
        """Load LED configuration from file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.three_led_keys = set(data.get('three_led_keys', []))
                    print(f"Loaded LED configuration: {len(self.three_led_keys)} keys with 3 LEDs")
            except Exception as e:
                print(f"Error loading LED config: {e}")
                self.three_led_keys = set()
        else:
            # No config file exists, use empty set (all keys use 2 LEDs by default)
            self.three_led_keys = set()
    
    def save_config(self):
        """Save LED configuration to file."""
        try:
            data = {
                'three_led_keys': sorted(list(self.three_led_keys))
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved LED configuration: {len(self.three_led_keys)} keys with 3 LEDs")
            return True
        except Exception as e:
            print(f"Error saving LED config: {e}")
            return False
    
    def set_three_led_key(self, key, enabled):
        """Set whether a key should use 3 LEDs."""
        if enabled:
            self.three_led_keys.add(key)
        else:
            self.three_led_keys.discard(key)
    
    def is_three_led_key(self, key):
        """Check if a key uses 3 LEDs."""
        return key in self.three_led_keys
    
    def toggle_three_led_key(self, key):
        """Toggle whether a key uses 3 LEDs."""
        if key in self.three_led_keys:
            self.three_led_keys.discard(key)
            return False
        else:
            self.three_led_keys.add(key)
            return True
    
    def get_config_bytes(self):
        """
        Generate configuration bytes for Arduino.
        Returns a bytearray encoding which keys use 3 LEDs.
        Format: 9 bytes, each byte represents 8 keys (72 keys total = 9 bytes)
        Bit is 1 if key uses 3 LEDs, 0 if it uses 2 LEDs.
        """
        config_bytes = bytearray(9)  # 72 keys / 8 bits per byte = 9 bytes
        for key in self.three_led_keys:
            if 0 <= key < 72:
                byte_index = key // 8
                bit_index = key % 8
                config_bytes[byte_index] |= (1 << bit_index)
        return config_bytes
