"""
LED Configuration Manager
Handles saving and loading LED mapping configuration for the keyboard.
"""
import json
import os

CONFIG_FILE = "led_config.json"

class LEDConfigManager:
    def __init__(self):
        # Configuration: LED count for each key (1, 2, or 3 LEDs)
        # Default is 2 LEDs for all keys
        self.led_counts = {}  # key -> count (1, 2, or 3)
        self.load_config()
    
    def load_config(self):
        """Load LED configuration from file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    # Support both old and new format
                    if 'led_counts' in data:
                        # New format: dict of key -> count
                        self.led_counts = {int(k): v for k, v in data['led_counts'].items()}
                    elif 'three_led_keys' in data:
                        # Old format: list of 3-LED keys, convert to new format
                        self.led_counts = {}
                        for key in data['three_led_keys']:
                            self.led_counts[key] = 3
                    print(f"Loaded LED configuration: {len(self.led_counts)} keys with custom LED counts")
            except Exception as e:
                print(f"Error loading LED config: {e}")
                self.led_counts = {}
        else:
            # No config file exists, use empty dict (all keys use 2 LEDs by default)
            self.led_counts = {}
    
    def save_config(self):
        """Save LED configuration to file."""
        try:
            data = {
                'led_counts': {str(k): v for k, v in self.led_counts.items()}
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved LED configuration: {len(self.led_counts)} keys with custom LED counts")
            return True
        except Exception as e:
            print(f"Error saving LED config: {e}")
            return False
    
    def get_led_count(self, key):
        """Get LED count for a key (1, 2, or 3). Default is 2."""
        return self.led_counts.get(key, 2)
    
    def set_led_count(self, key, count):
        """Set LED count for a key (1, 2, or 3)."""
        if count < 1 or count > 3:
            return
        if count == 2:
            # Remove from dict if setting to default
            self.led_counts.pop(key, None)
        else:
            self.led_counts[key] = count
    
    def cycle_led_count(self, key):
        """Cycle LED count for a key: 1 -> 2 -> 3 -> 1."""
        current = self.get_led_count(key)
        next_count = (current % 3) + 1  # 1->2, 2->3, 3->1
        self.set_led_count(key, next_count)
        return next_count
    
    # Legacy compatibility methods
    def is_three_led_key(self, key):
        """Check if a key uses 3 LEDs (legacy compatibility)."""
        return self.get_led_count(key) == 3
    
    def toggle_three_led_key(self, key):
        """Toggle between 2 and 3 LEDs (legacy compatibility)."""
        current = self.get_led_count(key)
        if current == 3:
            self.set_led_count(key, 2)
            return False
        else:
            self.set_led_count(key, 3)
            return True
    
    def get_config_bytes(self):
        """
        Generate configuration bytes for Arduino.
        Returns a bytearray encoding LED count for each key.
        Format: 18 bytes, 2 bits per key (72 keys total)
        00 = 2 LEDs (default), 01 = 1 LED, 10 = 3 LEDs
        """
        config_bytes = bytearray(18)  # 72 keys * 2 bits = 144 bits = 18 bytes
        
        for key in range(72):
            count = self.get_led_count(key)
            # Convert count to 2-bit value: 1->01, 2->00, 3->10
            if count == 1:
                value = 1
            elif count == 3:
                value = 2
            else:
                value = 0
            
            byte_index = (key * 2) // 8
            bit_offset = (key * 2) % 8
            config_bytes[byte_index] |= (value << bit_offset)
        
        return config_bytes
