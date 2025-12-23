"""
Configuration Mode Window for LED Keyboard Mapping
This window allows users to configure which keys use 1, 2, or 3 LEDs.
"""

import pygame
from Config import *
from GUI.Visuals import SimpleButton, SimpleKeyboard

class ConfigModeWindow:
    """Configuration mode for LED keyboard mapping"""
    
    def __init__(self, keyboard_config):
        self.keyboard_config = keyboard_config
        self.running = True
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 20)
        
        # Current LED count selection (1, 2, or 3)
        self.selected_led_count = 2
        
        # Buttons
        self.buttons = []
        margin = 20
        button_height = 40
        button_width = 120
        
        # LED count selection buttons
        by = margin
        bx = margin
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "1 LED", self.font, 
            lambda: self._set_led_count(1)))
        bx += button_width + 10
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "2 LEDs", self.font, 
            lambda: self._set_led_count(2)))
        bx += button_width + 10
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "3 LEDs", self.font, 
            lambda: self._set_led_count(3)))
        
        # Action buttons
        bx = WINDOW_WIDTH - margin - button_width * 3 - 20
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "Reset", self.font, 
            self._reset_config))
        bx += button_width + 10
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "Save", self.font, 
            self._save_and_exit))
        bx += button_width + 10
        self.buttons.append(SimpleButton(
            bx, by, button_width, button_height, "Cancel", self.font, 
            self._cancel))
        
        # Test all LEDs button
        test_button_y = by + button_height + 10
        self.buttons.append(SimpleButton(
            margin, test_button_y, button_width * 2, button_height, 
            "Test All LEDs", self.font, self._test_all_leds))
        
        # Keyboard visualization
        keyboard_height = 120
        keyboard_y = WINDOW_HEIGHT - keyboard_height - margin
        keyboard_width = WINDOW_WIDTH - 2 * margin
        self.keyboard = SimpleKeyboard(margin, keyboard_y, keyboard_width, keyboard_height, NUM_KEYS)
        
        # Track which key was just clicked for visual feedback
        self.last_clicked_key = None
        self.test_mode = False
        
    def _set_led_count(self, count):
        """Set the selected LED count"""
        self.selected_led_count = count
    
    def _reset_config(self):
        """Reset configuration to defaults"""
        self.keyboard_config.reset_to_defaults()
        self.last_clicked_key = None
    
    def _save_and_exit(self):
        """Save configuration and exit"""
        self.keyboard_config.save()
        self.running = False
        self.saved = True
    
    def _cancel(self):
        """Cancel without saving"""
        self.running = False
        self.saved = False
    
    def _test_all_leds(self):
        """Toggle test mode - lights up all LEDs"""
        self.test_mode = not self.test_mode
    
    def _handle_keyboard_click(self, pos):
        """Handle click on keyboard to set LED count for a key"""
        # Convert screen position to keyboard-relative position
        kb_x = pos[0] - self.keyboard.x
        kb_y = pos[1] - self.keyboard.y
        
        # Check if click is within keyboard bounds
        if kb_y < 0 or kb_y > self.keyboard.height:
            return
        
        # Find which key was clicked
        for i, key_data in enumerate(self.keyboard.key_rects):
            if key_data["rect"].collidepoint(kb_x, kb_y):
                # Set the LED count for this key
                self.keyboard_config.set_led_count(i, self.selected_led_count)
                self.last_clicked_key = i
                return
    
    def _get_key_colors(self):
        """Get colors for each key based on LED count"""
        colors = {}
        for i in range(NUM_KEYS):
            led_count = self.keyboard_config.get_led_count(i)
            
            if self.test_mode:
                # In test mode, all keys are bright
                colors[i] = MAX_BRIGHTNESS
            elif i == self.last_clicked_key:
                # Highlight the last clicked key
                colors[i] = MAX_BRIGHTNESS
            else:
                # Color based on LED count
                if led_count == 1:
                    colors[i] = MAX_BRIGHTNESS // 3  # Dim for 1 LED
                elif led_count == 2:
                    colors[i] = MAX_BRIGHTNESS // 2  # Medium for 2 LEDs (default)
                elif led_count == 3:
                    colors[i] = MAX_BRIGHTNESS  # Bright for 3 LEDs
        
        return colors
    
    def run(self, screen):
        """Run the configuration mode window"""
        clock = pygame.time.Clock()
        self.saved = False
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.saved = False
                
                # Handle button events
                for btn in self.buttons:
                    btn.handle_event(event)
                
                # Handle keyboard clicks
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_keyboard_click(event.pos)
            
            # Update keyboard visualization
            key_colors = self._get_key_colors()
            self.keyboard.set_active(key_colors)
            
            # Draw
            screen.fill(BLACK)
            
            # Draw title
            title_text = "LED Configuration Mode"
            title_surf = self.font.render(title_text, True, WHITE)
            screen.blit(title_surf, (WINDOW_WIDTH // 2 - title_surf.get_width() // 2, 10))
            
            # Draw instructions
            instructions = [
                f"Selected: {self.selected_led_count} LED{'s' if self.selected_led_count > 1 else ''}",
                "Click a key to assign LED count",
                "Colors: Dim=1 LED, Medium=2 LEDs, Bright=3 LEDs"
            ]
            y_offset = 90
            for instruction in instructions:
                inst_surf = self.small_font.render(instruction, True, GRAY)
                screen.blit(inst_surf, (20, y_offset))
                y_offset += 25
            
            # Draw LED count info
            info_y = WINDOW_HEIGHT - 200
            info_lines = [
                f"Total LEDs needed: {self.keyboard_config.get_total_led_count()}",
                f"1-LED keys: {len(self.keyboard_config.get_single_led_keys())}",
                f"3-LED keys: {len(self.keyboard_config.get_triple_led_keys())}"
            ]
            for line in info_lines:
                info_surf = self.small_font.render(line, True, CYAN)
                screen.blit(info_surf, (20, info_y))
                info_y += 25
            
            # Draw keyboard
            self.keyboard.draw(screen)
            
            # Draw buttons
            for i, btn in enumerate(self.buttons):
                # Highlight selected LED count button
                if i < 3 and i + 1 == self.selected_led_count:
                    # Draw a border around selected button
                    pygame.draw.rect(screen, GREEN, btn.rect.inflate(4, 4), 3, border_radius=8)
                btn.draw(screen)
            
            # Highlight test button if active
            if self.test_mode:
                test_btn = self.buttons[6]  # Test All LEDs button
                pygame.draw.rect(screen, GREEN, test_btn.rect.inflate(4, 4), 3, border_radius=8)
            
            pygame.display.flip()
            clock.tick(FPS)
        
        return self.saved
