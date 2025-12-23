"""
Keyboard LED Configuration Management
This module handles saving, loading, and managing LED configurations for different keyboards.
"""

import json
import os
from Config import NUM_KEYS

DEFAULT_CONFIG_FILE = "keyboard_config.json"

class KeyboardConfig:
    """Manages LED configuration for keyboard keys"""
    
    def __init__(self):
        # Default configuration: keys use 2 LEDs except for specific keys
        # Key index -> number of LEDs (1, 2, or 3)
        self.led_counts = [2] * NUM_KEYS
        
        # Set default single LED keys (matching Arduino firmware defaults)
        default_single_led_keys = [17, 11, 36]
        for key in default_single_led_keys:
            if key < NUM_KEYS:
                self.led_counts[key] = 1
    
    def set_led_count(self, key_index, count):
        """Set the number of LEDs for a specific key"""
        if 0 <= key_index < NUM_KEYS and count in [1, 2, 3]:
            self.led_counts[key_index] = count
    
    def get_led_count(self, key_index):
        """Get the number of LEDs for a specific key"""
        if 0 <= key_index < NUM_KEYS:
            return self.led_counts[key_index]
        return 2  # Default
    
    def get_single_led_keys(self):
        """Get list of keys that use only 1 LED"""
        return [i for i in range(NUM_KEYS) if self.led_counts[i] == 1]
    
    def get_triple_led_keys(self):
        """Get list of keys that use 3 LEDs"""
        return [i for i in range(NUM_KEYS) if self.led_counts[i] == 3]
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.led_counts = [2] * NUM_KEYS
        default_single_led_keys = [17, 11, 36]
        for key in default_single_led_keys:
            if key < NUM_KEYS:
                self.led_counts[key] = 1
    
    def save(self, filename=DEFAULT_CONFIG_FILE):
        """Save configuration to a JSON file"""
        config_data = {
            "version": "1.0",
            "led_counts": self.led_counts
        }
        try:
            # Save in the same directory as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(script_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def load(self, filename=DEFAULT_CONFIG_FILE):
        """Load configuration from a JSON file"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(script_dir, filename)
            
            if not os.path.exists(filepath):
                return False
            
            with open(filepath, 'r') as f:
                config_data = json.load(f)
            
            if "led_counts" in config_data:
                # Validate and load LED counts
                led_counts = config_data["led_counts"]
                if len(led_counts) == NUM_KEYS:
                    # Validate all values are 1, 2, or 3
                    if all(count in [1, 2, 3] for count in led_counts):
                        self.led_counts = led_counts
                        return True
            return False
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def export_for_arduino(self):
        """
        Export configuration in a format suitable for Arduino firmware.
        Returns tuple of (single_led_keys, triple_led_keys) arrays.
        """
        single_led_keys = self.get_single_led_keys()
        triple_led_keys = self.get_triple_led_keys()
        return single_led_keys, triple_led_keys
    
    def get_total_led_count(self):
        """Calculate total number of LEDs needed for this configuration"""
        # Start with 4 LEDs offset (as per Arduino firmware)
        total = 4
        for count in self.led_counts:
            total += count
        return total
