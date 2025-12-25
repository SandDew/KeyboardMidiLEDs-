import pygame
import threading
import time
from tkinter import filedialog, simpledialog
import tkinter as tk
import serial
import sys
import os

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Config import *
from GUI.Visuals import SimpleButton, SimpleKeyboard, SimpleDropdown, SimpleSlider
from LED_Config import LEDConfigManager

CLEAR_FLAG = 0x02  # clear command (must match firmware)
CONFIG_FLAG = 0x03  # configuration command (must match firmware)
CONFIG_MODE_ENTER = 0x04  # enter configuration mode
CONFIG_MODE_EXIT = 0x05  # exit configuration mode
CONFIG_MODE_TOGGLE = 0x06  # toggle 3-LED status

class MidiPlayerGUI:
    def __init__(self, initial_state=None):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Keyboard MIDI LED Player (Reworked)")

        # Serial connection
        self.ser = None
        self.serial_connected = False
        self._try_connect_serial()

        # Fonts
        self.font = pygame.font.Font(None, 28)

        # UI Layout
        self.margin = 20
        self.button_height = 40
        self.button_width = 140
        self.button_spacing = 10
        self.speed_dropdown_width = 160
        self.clear_button_width = 120
        self.config_button_width = 130
        self.skip_button_width = 40
        self.keyboard_height = KEYBOARD_HEIGHT
        self.keyboard_width = WINDOW_WIDTH - 2 * self.margin

        # Speed options - add Custom option
        self.speeds = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, "Custom..."]
        self.speed_index = 2  # Default to 1.0x
        self.custom_speed = None  # Track custom speed value
        
        # Fade time (fixed)
        self.fade_time = FADE_RANGE

        # Buttons (centered at the top)
        self.buttons = []
        total_width = (self.button_width + self.button_height + 
                      self.speed_dropdown_width + self.clear_button_width + 
                      self.config_button_width + self.skip_button_width * 2 + 
                      self.button_spacing * 6)
        bx = (WINDOW_WIDTH - total_width) // 2
        by = self.margin
        self.buttons.append(SimpleButton(
            bx, by, self.button_width, self.button_height, "Select MIDI", self.font, self.select_midi))
        bx += self.button_width + self.button_spacing
        # Play/Pause button with symbol
        self.buttons.append(SimpleButton(
            bx, by, self.button_height, self.button_height, "", self.font, self.toggle_playpause,
            is_playpause=True, get_state=lambda: self.playing and not self.paused
        ))

        # Speed dropdown - position dropdown menu below the slider
        bx += self.button_height + self.button_spacing
        slider_y = by + self.button_height + 18
        dropdown_menu_y = slider_y + 20  # Position below slider
        self.speed_dropdown = SimpleDropdown(
            bx, by, self.speed_dropdown_width, self.button_height, self._get_speed_labels(), self.font, 
            self._on_speed_change, self.speed_index, dropdown_y_override=dropdown_menu_y
        )

        # Clear keyboard button
        bx += self.speed_dropdown_width + self.button_spacing
        self.buttons.append(SimpleButton(
            bx, by, self.clear_button_width, self.button_height, "Clear Keys", self.font, self.clear_keyboard))

        # Configuration button
        bx += self.clear_button_width + self.button_spacing
        self.buttons.append(SimpleButton(
            bx, by, self.config_button_width, self.button_height, "Configure", self.font, self.toggle_config_mode))

        # Add skip buttons with symbols for compactness
        bx += self.config_button_width + self.button_spacing
        self.buttons.append(SimpleButton(
            bx, by, self.skip_button_width, self.button_height, "⏮", self.font, self.skip_back))
        bx += self.skip_button_width + self.button_spacing
        self.buttons.append(SimpleButton(
            bx, by, self.skip_button_width, self.button_height, "⏭", self.font, self.skip_forward))

        # Playhead slider below buttons (60% width, centered)
        slider_width = int(self.keyboard_width * 0.6)
        slider_x = (WINDOW_WIDTH - slider_width) // 2
        slider_y = by + self.button_height + 18
        self.playhead_slider = SimpleSlider(
            slider_x, slider_y, slider_width, 18, 0.0, 1.0, 0.0, self._on_slider_change
        )

        # Keyboard
        self.keyboard_y = WINDOW_HEIGHT - self.keyboard_height - self.margin
        self.keyboard = SimpleKeyboard(self.margin, self.keyboard_y, self.keyboard_width, self.keyboard_height, NUM_KEYS)

        # MIDI state
        self.midi_file = None
        self.note_times = None
        self.midi_length = 0
        self.playing = False
        self.paused = False
        self.playhead = 0.0
        self.speed = self.speeds[self.speed_index]
        self.user_exit = False

        # Configuration mode
        self.config_mode = False
        self.led_config = LEDConfigManager()

        # Threading
        self.running = True
        self.clock = pygame.time.Clock()
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.serial_monitor_thread = threading.Thread(target=self._serial_monitor_loop, daemon=True)
        self.serial_monitor_thread.start()

        # Restore previous session state if provided
        if initial_state:
            self._restore_state(initial_state)

    def _try_connect_serial(self):
        """Try to connect to serial device"""
        while not self.serial_connected:
            self._connect_once()
            if self.serial_connected:
                break
            time.sleep(2)

    def _connect_once(self):
        """Single attempt to open the serial port without blocking forever."""
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            self.ser = ser
            self.serial_connected = True
            print(f"Connected to keyboard on {SERIAL_PORT}")
        except Exception as e:
            self._handle_serial_error(e)

    def _handle_serial_error(self, exc=None):
        """Mark serial as disconnected and close the port safely."""
        self.serial_connected = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        if exc:
            print(f"Serial disconnected: {exc}")

    def _serial_monitor_loop(self):
        """Background loop to re-attempt connection whenever it is lost."""
        while True:
            if hasattr(self, "running") and not self.running:
                break
            if not self.serial_connected:
                self._connect_once()
            time.sleep(2)

    def _get_speed_labels(self):
        """Get speed labels including custom speed if set."""
        labels = []
        for speed in self.speeds:
            if speed == "Custom...":
                if self.custom_speed is not None:
                    labels.append(f"{self.custom_speed}x (Custom)")
                else:
                    labels.append("Custom...")
            else:
                labels.append(f"{speed}x")
        return labels

    def _prompt_custom_speed(self):
        """Prompt user for custom speed input."""
        root = tk.Tk()
        root.withdraw()
        
        # Get current speed as default
        current_speed = self.custom_speed if self.custom_speed is not None else self.speed
        
        try:
            speed_str = simpledialog.askstring(
                "Custom Speed", 
                f"Enter playback speed (e.g., 0.6, 0.7, 1.3):",
                initialvalue=str(current_speed)
            )
            
            if speed_str:
                try:
                    custom_speed = float(speed_str)
                    if 0.1 <= custom_speed <= 10.0:  # Reasonable speed limits
                        return custom_speed
                    else:
                        print("Speed must be between 0.1 and 10.0")
                except ValueError:
                    print("Invalid speed value entered")
        except Exception as e:
            print(f"Error getting custom speed: {e}")
        finally:
            try:
                root.destroy()
            except:
                pass  # Ignore errors if root is already destroyed
        
        return None

    def _on_speed_change(self, idx):
        old_speed = self.speed
        
        # Check if Custom option was selected
        if idx == len(self.speeds) - 1:  # "Custom..." is last item
            custom_speed = self._prompt_custom_speed()
            if custom_speed is not None:
                self.custom_speed = custom_speed
                self.speed = custom_speed
                self.speed_index = idx
                # Update dropdown to show custom speed
                self.speed_dropdown.options = self._get_speed_labels()
                self.speed_dropdown.selected_idx = idx
            else:
                # User cancelled or entered invalid value, revert to previous selection
                return
        else:
            # Regular speed option selected
            self.speed_index = idx
            self.speed = self.speeds[self.speed_index]
            self.custom_speed = None  # Clear custom speed when selecting preset
            # Update dropdown options to remove custom speed display
            self.speed_dropdown.options = self._get_speed_labels()
        
        # Adjust play_start_time to keep playhead position consistent when speed changes
        if self.playing and hasattr(self, 'play_start_time'):
            current_real_time = time.time()
            # Calculate where we should be based on the old speed
            elapsed_time = (current_real_time - self.play_start_time) * old_speed
            # Adjust start time for new speed to maintain same playhead position
            self.play_start_time = current_real_time - (elapsed_time / self.speed)

    def _on_slider_change(self, value):
        if self.midi_length > 0:
            self.playhead = value * self.midi_length
            if self.playing and hasattr(self, 'play_start_time'):
                # Adjust play_start_time when manually seeking
                self.play_start_time = time.time() - (self.playhead / self.speed)
            # Always update overlays and LEDs when seeking
            key_brightness = self._get_active_keys()
            self.keyboard.set_active(key_brightness)
            self.send_keys(key_brightness)

    def send_clear(self, timeout=0.02, max_retries=5):
        if not self.serial_connected or not self.ser:
            return False
        frame = bytearray([PACKET_START, 1, CLEAR_FLAG, 0, 0, PACKET_END])
        for _ in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start = time.time()
                while time.time() - start < timeout:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
                # retry
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False

    def send_keys(self, key_brightness_dict, timeout=0.02, max_retries=10):
        """Send key data; if no changes, issue clear command."""
        if not self.serial_connected:
            return False
        if not key_brightness_dict:
            return self.send_clear(timeout=timeout)
        
        count = len(key_brightness_dict)
        frame = bytearray([PACKET_START, count])
        for key, val in key_brightness_dict.items():
            frame.append(UPDATE_FLAG)
            frame.append(max(0, min(NUM_KEYS-1, int(key))))
            # Convert brightness to 0-99 range for hardware
            hardware_brightness = max(0, min(99, int(val * 99 / MAX_BRIGHTNESS)))
            frame.append(hardware_brightness)
        frame.append(PACKET_END)

        for attempt in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start_time = time.time()
                while True:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break  # immediately retry outer loop
                    if time.time() - start_time > timeout:
                        break  # immediately retry outer loop
                    # No sleep here: tight retry
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False

    def clear_keyboard(self):
        """Use firmware clear command instead of per-key packets."""
        if self.serial_connected:
            self.send_clear()
        self.keyboard.set_active({})
    
    def toggle_config_mode(self):
        """Toggle configuration mode for LED mapping."""
        self.config_mode = not self.config_mode
        
        if self.config_mode:
            # Entering config mode
            # Stop playback
            if self.playing:
                self.playing = False
                self.paused = False
            
            # Send command to Arduino to enter config mode (turns on all LEDs)
            if self.serial_connected:
                self.send_config_mode_enter()
            
            # Update GUI to show all keys as active
            key_brightness = {i: MAX_BRIGHTNESS for i in range(NUM_KEYS)}
            self.keyboard.set_active(key_brightness)
        else:
            # Exiting config mode
            # Save configuration
            self.led_config.save_config()
            
            # Send configuration to Arduino
            if self.serial_connected:
                config_bytes = self.led_config.get_config_bytes()
                self.send_config(config_bytes)
                # Exit config mode on Arduino
                self.send_config_mode_exit()
            
            # Clear GUI display
            self.keyboard.set_active({})
    
    def send_config_mode_enter(self, timeout=0.02, max_retries=5):
        """Send command to enter configuration mode."""
        if not self.serial_connected or not self.ser:
            return False
        
        frame = bytearray([PACKET_START, 1, CONFIG_MODE_ENTER, 0, 0, PACKET_END])
        for _ in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start = time.time()
                while time.time() - start < timeout:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False
    
    def send_config_mode_exit(self, timeout=0.02, max_retries=5):
        """Send command to exit configuration mode."""
        if not self.serial_connected or not self.ser:
            return False
        
        frame = bytearray([PACKET_START, 1, CONFIG_MODE_EXIT, 0, 0, PACKET_END])
        for _ in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start = time.time()
                while time.time() - start < timeout:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False
    
    def send_config_mode_toggle(self, key, timeout=0.02, max_retries=5):
        """Send command to toggle 3-LED status for a key."""
        if not self.serial_connected or not self.ser:
            return False
        
        frame = bytearray([PACKET_START, 1, CONFIG_MODE_TOGGLE, key, 0, PACKET_END])
        for _ in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start = time.time()
                while time.time() - start < timeout:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False
    
    def _handle_config_mode_click(self, key):
        """Handle clicking on a key in configuration mode."""
        if not self.config_mode:
            return
        
        # Cycle LED count for the clicked key locally (1 -> 2 -> 3 -> 1)
        new_count = self.led_config.cycle_led_count(key)
        
        # Send toggle command to Arduino to update LED mapping in real-time
        if self.serial_connected:
            self.send_config_mode_toggle(key)
    
    def send_config(self, config_bytes, timeout=0.02, max_retries=5):
        """Send LED configuration to Arduino (18 bytes)"""
        if not self.serial_connected or not self.ser:
            return False
        
        # Send 18 triplets: CONFIG_FLAG, byte_index, byte_value
        frame = bytearray([PACKET_START, 18])
        for i, byte_val in enumerate(config_bytes):
            frame.append(CONFIG_FLAG)
            frame.append(i)  # byte index
            frame.append(byte_val)
        frame.append(PACKET_END)
        
        for _ in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start = time.time()
                while time.time() - start < timeout:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
            except Exception as e:
                self._handle_serial_error(e)
                break
        return False

    def select_midi(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select MIDI File",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*")]
        )
        root.destroy()
        if file_path:
            from MIDI_Parser import parse_midi_file

            try:
                self.midi_file = file_path
                self.note_times, self.midi_length = parse_midi_file(file_path)
                self.playhead = 0.0
                # Reset slider to 0
                self.playhead_slider.set_value(0.0)
                # Stop playback if currently playing
                if self.playing:
                    self.playing = False
                    self.paused = False
                    if hasattr(self, 'play_start_time'):
                        delattr(self, 'play_start_time')
                # Clear keys to ensure all LEDs are off
                self.clear_keyboard()
            except Exception as e:
                print(f"Error loading MIDI file: {e}")
                self.midi_file = None
                self.note_times = None
                self.midi_length = 0

    def _restore_state(self, state):
        """Restore last known state after a crash restart."""
        try:
            midi_path = state.get("midi_file") if state else None
            playhead = state.get("playhead", 0.0) if state else 0.0
            speed = state.get("speed") if state else None
            speed_index = state.get("speed_index") if state else None
            custom_speed = state.get("custom_speed") if state else None

            if midi_path and os.path.exists(midi_path):
                from MIDI_Parser import parse_midi_file
                self.midi_file = midi_path
                self.note_times, self.midi_length = parse_midi_file(midi_path)
                self.playhead = min(playhead, self.midi_length)
                if self.midi_length > 0:
                    self.playhead_slider.set_value(self.playhead / self.midi_length)
            # Restore speed settings
            if speed is not None:
                self.speed = speed
            if speed_index is not None and 0 <= speed_index < len(self.speeds):
                self.speed_index = speed_index
            self.custom_speed = custom_speed
        except Exception as e:
            print(f"Failed to restore previous state: {e}")

    def toggle_playpause(self):
        if not self.note_times:
            return
        if not self.playing:
            self.playing = True
            self.paused = False
            # Ensure we don't trigger notes at t=0 unless there are actual notes there
            if self.playhead == 0.0:
                # Check if there are any notes exactly at t=0
                has_notes_at_zero = any(
                    any(start_time == 0.0 for start_time, _ in self.note_times[key]) 
                    for key in range(min(NUM_KEYS, len(self.note_times)))
                )
                if not has_notes_at_zero:
                    self.clear_keyboard()
            
            self.play_start_time = time.time() - (self.playhead / self.speed)
        else:
            if self.paused:
                self.paused = False
                self.play_start_time = time.time() - (self.playhead / self.speed)
            else:
                self.paused = True

    def _update_loop(self):
        while self.running:
            if self.playing and not self.paused and self.note_times:
                self._update_playback()
            elif self.playing and self.paused and self.note_times:
                # When paused, continuously send current key states
                key_brightness = self._get_current_key_states()
                if self.serial_connected:
                    self.send_keys(key_brightness)
            time.sleep(UPDATE_RATE)

    def _get_current_key_states(self):
        """Get the current key brightness states at the current playhead position."""
        if not self.note_times:
            return {}
        
        # First, get all upcoming note times to determine priority
        upcoming_notes = self._get_upcoming_note_times()
        
        key_brightness = {}
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                notes = self.note_times[key]
                # Find the next note-on time for this key
                next_note_on = None
                for t_on, _ in notes:
                    if t_on >= self.playhead:
                        next_note_on = t_on
                        break

                brightness = 0
                # Calculate brightness based on current playhead position
                if next_note_on is not None:
                    dt = next_note_on - self.playhead
                    if 0 < dt < self.fade_time:
                        base_brightness = int(MAX_BRIGHTNESS * (1 - dt / self.fade_time))
                        # Apply priority-based brightness reduction
                        priority = self._get_note_priority(next_note_on, upcoming_notes)
                        brightness = self._apply_priority_brightness(base_brightness, priority)
                    elif abs(self.playhead - next_note_on) < UPDATE_RATE * 1.5:
                        brightness = 0
                
                if brightness > 0:
                    key_brightness[key] = brightness
        
        return key_brightness

    def _find_active_noteset_time(self, direction=1):
        """Find the next/previous set of notes (chord) time after/before current playhead."""
        if not self.note_times:
            return None
        all_times = set()
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                for start_time, end_time in self.note_times[key]:
                    all_times.add(start_time)
        all_times = sorted(all_times)
        if not all_times:
            return None
        if direction > 0:
            # Next set
            for t in all_times:
                if t > self.playhead + 1e-6:
                    return t
            return all_times[-1]
        else:
            # Previous set
            prev = all_times[0]
            for t in all_times:
                if t >= self.playhead - 1e-6:
                    return prev
                prev = t
            return all_times[0]

    def skip_forward(self):
        """Skip to the next set of notes (chord) and light only those notes, update overlays and LEDs."""
        t = self._find_active_noteset_time(direction=1)
        if t is not None:
            self.playing = False
            self.paused = False
            self.playhead = t
            if hasattr(self, 'play_start_time'):
                delattr(self, 'play_start_time')
            # Update overlays and LEDs as if seeking
            key_brightness = self._get_active_keys()
            self.clear_keyboard()
            self.keyboard.set_active(key_brightness)
            self.send_keys(key_brightness)

    def skip_back(self):
        """Skip to the previous set of notes (chord) and light only those notes, update overlays and LEDs."""
        t = self._find_active_noteset_time(direction=-1)
        if t is not None:
            self.playing = False
            self.paused = False
            self.playhead = t
            if hasattr(self, 'play_start_time'):
                delattr(self, 'play_start_time')
            # Update overlays and LEDs as if seeking
            key_brightness = self._get_active_keys()
            self.clear_keyboard()
            self.keyboard.set_active(key_brightness)
            self.send_keys(key_brightness)

    def _show_notes_at_time(self, t):
        """Turn off all lights, then turn on only the notes at time t, and update GUI overlays."""
        key_brightness = {}
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                for start_time, end_time in self.note_times[key]:
                    if abs(start_time - t) < 1e-6:
                        key_brightness[key] = MAX_BRIGHTNESS
                        break
        self.clear_keyboard()
        self.keyboard.set_active(key_brightness)
        self.send_keys(key_brightness)

    def _update_playback(self):
        """LED fades in before note-on, turns off at note-on, never fades out after (sync with GUI)."""
        if not hasattr(self, 'play_start_time'):
            self.play_start_time = time.time() - self.playhead / self.speed

        current_time = (time.time() - self.play_start_time) * self.speed
        self.playhead = min(current_time, self.midi_length)

        if self.playhead >= self.midi_length:
            self.playing = False
            return

        # Get all upcoming note times to determine priority
        upcoming_notes = self._get_upcoming_note_times()

        key_brightness = {}
        keys_to_turn_off = set()
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                notes = self.note_times[key]
                # Find the next note-on time for this key
                next_note_on = None
                for t_on, _ in notes:
                    if t_on >= self.playhead:
                        next_note_on = t_on
                        break

                brightness = 0
                # Fade in before note-on only
                if next_note_on is not None:
                    dt = next_note_on - self.playhead
                    if 0 < dt < self.fade_time:
                        base_brightness = int(MAX_BRIGHTNESS * (1 - dt / self.fade_time))
                        # Apply priority-based brightness reduction
                        priority = self._get_note_priority(next_note_on, upcoming_notes)
                        brightness = self._apply_priority_brightness(base_brightness, priority)
                    # At the exact play time or after, turn off LED
                    if abs(self.playhead - next_note_on) < UPDATE_RATE * 1.5 or self.playhead > next_note_on:
                        brightness = 0
                        # Ensure we explicitly turn off the LED after the bar
                        keys_to_turn_off.add(key)
                # If fading in, set brightness
                if brightness > 0:
                    key_brightness[key] = brightness

        # Explicitly set keys that just finished their bar to 0 brightness
        for key in keys_to_turn_off:
            key_brightness[key] = 0

        if self.serial_connected:
            self.send_keys(key_brightness)
            
            # Send multiple turn-off commands for keys that should be off
            if keys_to_turn_off:
                for i in range(4):  # Send 4 additional times
                    time.sleep(0.005)  # Small delay between commands
                    turn_off_dict = {key: 0 for key in keys_to_turn_off}
                    self.send_keys(turn_off_dict)

    def _get_active_keys(self):
        """Get currently active keys for overlays with priority-based brightness."""
        if not self.note_times:
            return {}
        
        # Get all upcoming note times to determine priority
        upcoming_notes = []
        max_lookahead = self.playhead + UPDATE_RATE * 1.5
        upcoming_times = set()
        
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                for start_time, _ in self.note_times[key]:
                    if self.playhead <= start_time <= max_lookahead:
                        upcoming_times.add(start_time)
        
        upcoming_notes = sorted(upcoming_times)
        
        active = {}
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                notes = self.note_times[key]
                for t_on, t_off in notes:
                    if abs(self.playhead - t_on) < UPDATE_RATE * 1.5:
                        base_brightness = MAX_BRIGHTNESS
                        # Apply priority-based brightness reduction
                        priority = self._get_note_priority(t_on, upcoming_notes)
                        brightness = self._apply_priority_brightness(base_brightness, priority)
                        active[key] = brightness
                        break
        return active

    def _get_upcoming_note_times(self):
        """Get all upcoming note start times within the fade range, sorted by time."""
        if not self.note_times:
            return []
        
        upcoming_times = set()
        max_lookahead = self.playhead + self.fade_time
        
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                for start_time, _ in self.note_times[key]:
                    if self.playhead <= start_time <= max_lookahead:
                        upcoming_times.add(start_time)
        
        return sorted(upcoming_times)
    
    def _get_note_priority(self, note_time, upcoming_notes):
        """Get the priority of a note (0 = immediate next, 1 = second next, etc.)"""
        try:
            return upcoming_notes.index(note_time)
        except ValueError:
            return 0  # Default to highest priority if not found
    
    def _apply_priority_brightness(self, base_brightness, priority):
        """Apply brightness reduction based on note priority."""
        if priority == 0:
            # Immediate next notes get full brightness
            return base_brightness
        else:
            # Second and subsequent notes get quarter brightness
            return base_brightness // 4

    def _get_falling_notes(self):
        """Return a list of falling notes for visualization."""
        if not self.note_times or not self.playing:
            return []
        
        notes = []
        fall_time = 2.0  # Notes fall for 2 seconds before hitting the keyboard
        fall_area_height = self.keyboard_y - self.margin
        pixels_per_sec = fall_area_height / fall_time
        
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                for start_time, end_time in self.note_times[key]:
                    # Calculate when note should start falling (fall_time seconds before it plays)
                    fall_start_time = start_time - fall_time
                    
                    # Only show notes that should be visible now
                    if fall_start_time <= self.playhead <= end_time + 0.5:  # Show until 0.5s after note ends
                        # Calculate note position based on how long it's been falling
                        time_since_fall_start = self.playhead - fall_start_time
                        
                        if time_since_fall_start >= 0:  # Only show if fall has started
                            # Calculate position - note moves down as time progresses
                            y_position = self.margin + (time_since_fall_start * pixels_per_sec)
                            
                            # Calculate note height based on note duration
                            note_duration = end_time - start_time
                            height = max(8, min(30, note_duration * pixels_per_sec))
                            
                            # Only add note if it's still visible (not completely past the keyboard)
                            if y_position < self.keyboard_y + height:
                                notes.append({
                                    "note": key,
                                    "y": y_position - height,  # Start of note rectangle
                                    "h": height,
                                    "color": CYAN,
                                    "start_time": start_time,
                                    "end_time": end_time
                                })
        
        return notes
    
    def _draw_config_mode_overlay(self):
        """Draw overlay for configuration mode showing LED count for each key."""
        # Draw banner at top
        banner_height = 60
        banner_rect = pygame.Rect(0, self.margin + self.button_height + 50, WINDOW_WIDTH, banner_height)
        overlay = pygame.Surface((WINDOW_WIDTH, banner_height), pygame.SRCALPHA)
        overlay.fill((255, 140, 0, 180))  # Orange overlay
        self.screen.blit(overlay, banner_rect)
        
        # Draw text
        title_text = self.font.render("Configuration Mode", True, WHITE)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, banner_rect.centery - 10))
        self.screen.blit(title_text, title_rect)
        
        instruction_font = pygame.font.Font(None, 20)
        instruction_text = instruction_font.render("Click keys to cycle LED count: 1 LED (red), 2 LEDs (gray), 3 LEDs (green). Click Configure to save.", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, banner_rect.centery + 12))
        self.screen.blit(instruction_text, instruction_rect)
        
        # Draw overlay on keys with custom LED counts
        for key in range(NUM_KEYS):
            led_count = self.led_config.get_led_count(key)
            if key < len(self.keyboard.key_rects):
                k = self.keyboard.key_rects[key]
                rect = k["rect"].copy()
                rect.x += self.keyboard.x
                rect.y += self.keyboard.y
                key_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                
                # Choose color based on LED count
                if led_count == 1:
                    key_overlay.fill(CONFIG_MODE_1_LED)  # Red for 1 LED
                elif led_count == 3:
                    key_overlay.fill(CONFIG_MODE_3_LED)  # Green for 3 LEDs
                else:
                    # Don't show overlay for default 2 LEDs to reduce clutter
                    continue
                
                self.screen.blit(key_overlay, (rect.x, rect.y))

    def run(self):
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        self.user_exit = True
                    
                    # Handle keyboard clicks in configuration mode
                    if self.config_mode and event.type == pygame.MOUSEBUTTONDOWN:
                        clicked_key = self.keyboard.get_clicked_key(event.pos)
                        if clicked_key is not None:
                            self._handle_config_mode_click(clicked_key)
                    
                    for btn in self.buttons:
                        btn.handle_event(event)
                    self.speed_dropdown.handle_event(event)
                    self.playhead_slider.handle_event(event)

                # --- Update playhead position if playing ---
                if self.playing and not self.paused and self.midi_length > 0:
                    # Calculate playhead based on time and speed
                    if hasattr(self, 'play_start_time'):
                        current_time = (time.time() - self.play_start_time) * self.speed
                        self.playhead = min(current_time, self.midi_length)
                        if self.playhead >= self.midi_length:
                            self.playing = False

                # Update keyboard state
                if not self.config_mode:
                    self.keyboard.set_active(self._get_active_keys())
                    self.keyboard.set_falling_notes(self._get_falling_notes())
                else:
                    # In config mode, show which keys are selected for 3 LEDs
                    self.keyboard.set_falling_notes([])

                # Keep slider synced when not dragging
                if self.midi_length > 0 and not self.playhead_slider.dragging:
                    self.playhead_slider.set_value(self.playhead / self.midi_length)

                # Draw
                self.screen.fill(BLACK)
                self.keyboard.draw(self.screen)
                
                # Draw configuration mode overlay
                if self.config_mode:
                    self._draw_config_mode_overlay()
                
                self.playhead_slider.draw(self.screen)
                
                for btn in self.buttons:
                    btn.draw(self.screen)
                self.speed_dropdown.draw(self.screen)

                pygame.display.flip()
                self.clock.tick(FPS)
        finally:
            # Clean up serial connection
            if self.serial_connected and self.ser:
                try:
                    self.send_clear()
                except:
                    pass
                self.ser.close()
            pygame.quit()
            pygame.quit()

    def export_state(self):
        """Return a dict with the minimal state to restore after a crash."""
        return {
            "midi_file": self.midi_file,
            "playhead": self.playhead,
            "speed": self.speed,
            "speed_index": self.speed_index,
            "custom_speed": self.custom_speed,
        }
