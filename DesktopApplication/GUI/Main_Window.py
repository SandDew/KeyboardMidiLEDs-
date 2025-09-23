import pygame
import threading
import time
from tkinter import filedialog
import tkinter as tk
import serial
import sys
import os

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Config import *
from GUI.Visuals import SimpleButton, SimpleKeyboard, SimpleDropdown, SimpleSlider

class MidiPlayerGUI:
    def __init__(self):
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
        self.keyboard_height = KEYBOARD_HEIGHT
        self.keyboard_width = WINDOW_WIDTH - 2 * self.margin

        # Speed options
        self.speeds = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
        self.speed_index = 2  # Default to 1.0x

        # Buttons (centered at the top)
        self.buttons = []
        total_width = self.button_width + self.button_height + 10 + 160 + 10 + 120  # Added space for clear button
        bx = (WINDOW_WIDTH - total_width) // 2
        by = self.margin
        self.buttons.append(SimpleButton(
            bx, by, self.button_width, self.button_height, "Select MIDI", self.font, self.select_midi))
        bx += self.button_width + 10
        # Play/Pause button with symbol
        self.buttons.append(SimpleButton(
            bx, by, self.button_height, self.button_height, "", self.font, self.toggle_playpause,
            is_playpause=True, get_state=lambda: self.playing and not self.paused
        ))

        # Speed dropdown - position dropdown menu below the slider
        bx += self.button_height + 10
        slider_y = by + self.button_height + 18
        dropdown_menu_y = slider_y + 20  # Position below slider
        self.speed_dropdown = SimpleDropdown(
            bx, by, 160, self.button_height, [f"{s}x" for s in self.speeds], self.font, 
            self._on_speed_change, self.speed_index, dropdown_y_override=dropdown_menu_y
        )

        # Clear keyboard button
        bx += 170
        self.buttons.append(SimpleButton(
            bx, by, 120, self.button_height, "Clear Keys", self.font, self.clear_keyboard))

        # Add skip buttons with symbols for compactness
        bx_skip = bx + 140  # after clear button
        self.buttons.append(SimpleButton(
            bx_skip, by, 40, self.button_height, "⏮", self.font, self.skip_back))
        bx_skip += 50
        self.buttons.append(SimpleButton(
            bx_skip, by, 40, self.button_height, "⏭", self.font, self.skip_forward))

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

        # Threading
        self.running = True
        self.clock = pygame.time.Clock()
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _try_connect_serial(self):
        """Try to connect to serial device"""
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.serial_connected = True
            print(f"Connected to keyboard on {SERIAL_PORT}")
        except Exception as e:
            self.serial_connected = False
            self.ser = None
            print(f"Serial connection failed: {e}")

    def _on_speed_change(self, idx):
        old_speed = self.speed
        self.speed_index = idx
        self.speed = self.speeds[self.speed_index]
        
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

    def clear_keyboard(self):
        """Clear all keyboard LEDs"""
        if self.serial_connected and self.ser:
            # Send all keys off command - send each key individually with 0 brightness
            for key in range(NUM_KEYS):
                frame = bytearray([PACKET_START, 1])  # Send one key at a time
                frame.append(UPDATE_FLAG)
                frame.append(key)
                frame.append(0)  # Brightness 0
                frame.append(PACKET_END)
                
                try:
                    self.ser.write(frame)
                    self.ser.flush()
                    # Wait for acknowledgment
                    start_time = time.time()
                    while time.time() - start_time < 0.02:
                        if self.ser.in_waiting:
                            resp = self.ser.read(1)[0]
                            if resp == READY_FLAG:
                                break
                        time.sleep(0.001)
                except Exception as e:
                    print(f"Error clearing key {key}: {e}")
        
        # Clear visual keyboard
        self.keyboard.set_active({})

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
                # Clear keys twice to ensure all LEDs are off
                self.clear_keyboard()
                self.clear_keyboard()
                # Update keys/visuals to reflect new playhead (all off)
                self.keyboard.set_active({})
            except Exception as e:
                print(e)

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
            time.sleep(UPDATE_RATE)

    def send_keys(self, key_brightness_dict, timeout=0.02, max_retries=10):
        """Send key data to serial device using the working protocol, retry immediately if not READY_FLAG"""
        if not key_brightness_dict or not self.serial_connected:
            return False
        
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
            except Exception:
                break
        return False

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
                    if 0 < dt < FADE_RANGE:
                        brightness = int(MAX_BRIGHTNESS * (1 - dt / FADE_RANGE))
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

    def _get_active_keys(self):
        """Get currently active keys for overlays (unchanged)."""
        if not self.note_times:
            return {}
        active = {}
        for key in range(NUM_KEYS):
            if key < len(self.note_times):
                notes = self.note_times[key]
                for t_on, t_off in notes:
                    if abs(self.playhead - t_on) < UPDATE_RATE * 1.5:
                        active[key] = MAX_BRIGHTNESS
                        break
        return active

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

    def run(self):
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    for btn in self.buttons:
                        btn.handle_event(event)
                    self.speed_dropdown.handle_event(event)
                    self.playhead_slider.handle_event(event)

                # --- Update playhead position if playing ---
                if self.playing and not self.paused and self.midi_length > 0:
                    if hasattr(self, 'play_start_time'):
                        current_time = (time.time() - self.play_start_time) * self.speed
                        self.playhead = min(current_time, self.midi_length)
                        if self.playhead >= self.midi_length:
                            self.playing = False

                # Update keyboard state
                self.keyboard.set_active(self._get_active_keys())
                self.keyboard.set_falling_notes(self._get_falling_notes())

                # Keep slider synced when not dragging
                if self.midi_length > 0 and not self.playhead_slider.dragging:
                    self.playhead_slider.set_value(self.playhead / self.midi_length)

                # Draw
                self.screen.fill(BLACK)
                self.keyboard.draw(self.screen)
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
                    all_keys_off = {k: 0 for k in range(NUM_KEYS)}
                    frame = bytearray([PACKET_START, len(all_keys_off)])
                    for key, val in all_keys_off.items():
                        frame.append(UPDATE_FLAG)
                        frame.append(key)
                        frame.append(0)
                    frame.append(PACKET_END)
                    self.ser.write(frame)
                    self.ser.flush()
                except:
                    pass
                self.ser.close()
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
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
                self.keyboard.set_active(self._get_active_keys())
                self.keyboard.set_falling_notes(self._get_falling_notes())

                # Keep slider synced when not dragging
                if self.midi_length > 0 and not self.playhead_slider.dragging:
                    self.playhead_slider.set_value(self.playhead / self.midi_length)

                # Draw
                self.screen.fill(BLACK)
                self.keyboard.draw(self.screen)
                self.playhead_slider.draw(self.screen)
                for btn in self.buttons:
                    btn.draw(self.screen)
                self.speed_dropdown.draw(self.screen)

                pygame.display.flip()
                self.clock.tick(FPS)
        finally:
            # Clean up serial connection
            if self.serial_connected and self.ser:
                # Turn off all keys before disconnecting
                try:
                    all_keys_off = {k: 0 for k in range(NUM_KEYS)}
                    frame = bytearray([PACKET_START, len(all_keys_off)])
                    for key, val in all_keys_off.items():
                        frame.append(UPDATE_FLAG)
                        frame.append(key)
                        frame.append(0)
                    frame.append(PACKET_END)
                    self.ser.write(frame)
                    self.ser.flush()
                except:
                    pass
                self.ser.close()

            pygame.quit()
