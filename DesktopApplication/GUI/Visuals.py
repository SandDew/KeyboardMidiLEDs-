import pygame
from Config import *

# Initialize pygame font module
pygame.font.init()

class SimpleButton:
    def __init__(self, x, y, w, h, text, font, callback=None, is_playpause=False, get_state=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.callback = callback
        self.hovered = False
        self.pressed = False
        self.is_playpause = is_playpause
        self.get_state = get_state  # Should return True if playing, False if paused

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                if self.callback:
                    self.callback()
                return True
            self.pressed = False
        return False

    def draw(self, surf):
        color = BUTTON_COLOR
        if self.pressed:
            color = BUTTON_PRESSED
        elif self.hovered:
            color = BUTTON_HOVER
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=6)
        if self.is_playpause and self.get_state:
            # Draw play or pause symbol
            center = self.rect.center
            size = self.rect.height // 2
            if self.get_state():
                # Draw pause symbol
                bar_w = size // 4
                bar_h = size
                gap = bar_w
                x1 = center[0] - gap
                x2 = center[0] + gap
                y = center[1] - bar_h // 2
                pygame.draw.rect(surf, WHITE, (x1 - bar_w//2, y, bar_w, bar_h))
                pygame.draw.rect(surf, WHITE, (x2 - bar_w//2, y, bar_w, bar_h))
            else:
                # Draw play symbol
                points = [
                    (center[0] - size//3, center[1] - size//2),
                    (center[0] - size//3, center[1] + size//2),
                    (center[0] + size//2, center[1])
                ]
                pygame.draw.polygon(surf, WHITE, points)
        else:
            text_surf = self.font.render(self.text, True, WHITE)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surf.blit(text_surf, text_rect)

class SimpleDropdown:
    def __init__(self, x, y, w, h, options, font, callback=None, selected=0, dropdown_y_override=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.options = options
        self.font = font
        self.callback = callback
        self.selected = selected
        self.expanded = False
        self.hovered = False
        self.dropdown_y_override = dropdown_y_override  # Custom Y position for dropdown menu

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
                return True
            elif self.expanded:
                for i, _ in enumerate(self.options):
                    # Use override Y position if provided
                    dropdown_y = self.dropdown_y_override if self.dropdown_y_override else self.rect.y
                    option_rect = pygame.Rect(self.rect.x, dropdown_y + (i + 1) * self.rect.height, self.rect.width, self.rect.height)
                    if option_rect.collidepoint(event.pos):
                        self.selected = i
                        self.expanded = False
                        if self.callback:
                            self.callback(i)
                        return True
                self.expanded = False
        return False

    def draw(self, surf):
        color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=6)
        text_surf = self.font.render(str(self.options[self.selected]), True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surf.blit(text_surf, text_rect)
        # Draw dropdown arrow
        arrow_x = self.rect.right - 20
        arrow_y = self.rect.centery
        pygame.draw.polygon(surf, WHITE, [
            (arrow_x, arrow_y - 5),
            (arrow_x + 10, arrow_y - 5),
            (arrow_x + 5, arrow_y + 5)
        ])
        # Draw expanded options
        if self.expanded:
            # Use override Y position if provided
            dropdown_y = self.dropdown_y_override if self.dropdown_y_override else self.rect.y
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.rect.x, dropdown_y + (i + 1) * self.rect.height, self.rect.width, self.rect.height)
                pygame.draw.rect(surf, BUTTON_COLOR, option_rect, border_radius=6)
                pygame.draw.rect(surf, WHITE, option_rect, 1, border_radius=6)
                opt_surf = self.font.render(str(option), True, WHITE)
                opt_rect = opt_surf.get_rect(center=option_rect.center)
                surf.blit(opt_surf, opt_rect)

class SimpleSlider:
    def __init__(self, x, y, w, h, min_val, max_val, value=0.0, callback=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.callback = callback
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_value_from_mouse(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging:
                self.dragging = False
                if self.callback:
                    self.callback(self.value)
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_value_from_mouse(event.pos[0])
            return True
        return False

    def _set_value_from_mouse(self, mouse_x):
        rel_x = max(0, min(self.rect.width, mouse_x - self.rect.x))
        self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)

    def set_value(self, value):
        self.value = max(self.min_val, min(self.max_val, value))

    def draw(self, surf):
        # Draw track
        pygame.draw.rect(surf, DARK_GRAY, self.rect, border_radius=6)
        pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=6)
        # Draw handle
        handle_x = int(self.rect.x + ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width)
        handle_rect = pygame.Rect(handle_x - 7, self.rect.y - 4, 14, self.rect.height + 8)
        pygame.draw.rect(surf, BUTTON_COLOR, handle_rect, border_radius=8)
        pygame.draw.rect(surf, WHITE, handle_rect, 2, border_radius=8)

class SimpleKeyboard:
    def __init__(self, x, y, width, height, num_keys=72):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.num_keys = num_keys

        # Note pattern (C=0, C#=1, ..., B=11)
        self.note_pattern = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]  # 0=white, 1=black

        # Key geometry
        self.white_key_count = self._count_white_keys()
        self.white_key_width = self.width / self.white_key_count
        self.black_key_width = self.white_key_width * 0.6
        self.black_key_height = self.height * 0.6

        # Precompute key rects
        self.key_rects = self._compute_key_rects()
        self.active = [0] * self.num_keys

        # Initialize font for labels
        self.font = pygame.font.Font(None, 16)

        # Pre-render base
        self.base = pygame.Surface((self.width, self.height))
        self._draw_base()

        self.falling_notes = []

    def _count_white_keys(self):
        return sum(1 for i in range(self.num_keys) if self.note_pattern[i % 12] == 0)

    def _compute_key_rects(self):
        rects = []
        white_index = 0
        for i in range(self.num_keys):
            is_white = self.note_pattern[i % 12] == 0
            if is_white:
                x = white_index * self.white_key_width
                rects.append({
                    "rect": pygame.Rect(int(x), 0, int(self.white_key_width), self.height),
                    "is_white": True,
                    "note": i
                })
                white_index += 1
            else:
                x = (white_index - 1) * self.white_key_width + self.white_key_width - self.black_key_width / 2
                rects.append({
                    "rect": pygame.Rect(int(x), 0, int(self.black_key_width), int(self.black_key_height)),
                    "is_white": False,
                    "note": i
                })
        return rects

    def _draw_base(self):
        self.base.fill(BLACK)
        # White keys
        for k in self.key_rects:
            if k["is_white"]:
                pygame.draw.rect(self.base, WHITE, k["rect"])
                pygame.draw.rect(self.base, GRAY, k["rect"], 1)
        # Black keys
        for k in self.key_rects:
            if not k["is_white"]:
                pygame.draw.rect(self.base, BLACK, k["rect"])
                pygame.draw.rect(self.base, GRAY, k["rect"], 1)
        
        # Add middle C label (C4 is typically middle C, which would be note 24 in a 72-key setup starting from C2)
        middle_c_key = 24  # Adjust based on your key mapping
        if 0 <= middle_c_key < len(self.key_rects):
            k = self.key_rects[middle_c_key]
            if k["is_white"]:
                # Draw "C4" label at the bottom of the middle C key
                text_surface = self.font.render("C4", True, BLACK)
                text_rect = text_surface.get_rect()
                text_x = k["rect"].centerx - text_rect.width // 2
                text_y = k["rect"].bottom - text_rect.height - 5
                self.base.blit(text_surface, (text_x, text_y))

    def set_active(self, key_brightness_dict):
        self.active = [0] * self.num_keys
        for k, v in key_brightness_dict.items():
            if 0 <= k < self.num_keys:
                self.active[k] = v

    def set_falling_notes(self, falling_notes):
        self.falling_notes = falling_notes
    
    def get_clicked_key(self, mouse_pos):
        """Return the key index that was clicked, or None if no key was clicked."""
        # Adjust mouse position relative to keyboard position
        rel_x = mouse_pos[0] - self.x
        rel_y = mouse_pos[1] - self.y
        
        # Check if click is within keyboard bounds
        if rel_x < 0 or rel_x >= self.width or rel_y < 0 or rel_y >= self.height:
            return None
        
        # Check black keys first (they're on top)
        for k in self.key_rects:
            if not k["is_white"]:
                if k["rect"].collidepoint(rel_x, rel_y):
                    return k["note"]
        
        # Then check white keys
        for k in self.key_rects:
            if k["is_white"]:
                if k["rect"].collidepoint(rel_x, rel_y):
                    return k["note"]
        
        return None

    def draw(self, surf):
        # 1) Draw falling bars (white-first, then black) and track overlapped keys for overlays on keys
        overlap_white = set()
        overlap_black = set()
        if hasattr(self, "falling_notes"):
            # White key bars
            for note in self.falling_notes:
                k = self.key_rects[note["note"]]
                if not k["is_white"]:
                    continue
                x = k["rect"].x + self.x
                w = k["rect"].width
                y = int(note["y"])
                h = int(note.get("h", 18))
                color = CYAN
                if y + h <= self.y:
                    pygame.draw.rect(surf, color, (x, y, w, h), border_radius=4)
                else:
                    above_h = max(0, self.y - y)
                    if above_h > 0:
                        pygame.draw.rect(surf, color, (x, y, w, above_h), border_radius=4)
                    if h - above_h > 0:
                        overlap_white.add(note["note"])

            # Black key bars
            for note in self.falling_notes:
                k = self.key_rects[note["note"]]
                if k["is_white"]:
                    continue
                x = k["rect"].x + self.x
                w = k["rect"].width
                y = int(note["y"])
                h = int(note.get("h", 18))
                color = MAGENTA
                if y + h <= self.y:
                    pygame.draw.rect(surf, color, (x, y, w, h), border_radius=4)
                else:
                    above_h = max(0, self.y - y)
                    if above_h > 0:
                        pygame.draw.rect(surf, color, (x, y, w, above_h), border_radius=4)
                    if h - above_h > 0:
                        overlap_black.add(note["note"])

        # 2) Draw keyboard base
        surf.blit(self.base, (self.x, self.y))

        # 3) Draw overlays on WHITE keys only where bars overlap the keyboard
        for idx in overlap_white:
            k = self.key_rects[idx]
            if not k["is_white"]:
                continue
            rect = k["rect"].copy()
            rect.x += self.x
            rect.y += self.y
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((0, 120, 255, 160))
            surf.blit(overlay, (rect.x, rect.y))

        # 4) Draw overlays on BLACK keys only where bars overlap the keyboard
        for idx in overlap_black:
            k = self.key_rects[idx]
            if k["is_white"]:
                continue
            rect = k["rect"].copy()
            rect.x += self.x
            rect.y += self.y
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((255, 0, 255, 180))
            surf.blit(overlay, (rect.x, rect.y))

        # 5) Draw overlays for active keys - WHITE keys only get blue overlay
        for i, bright in enumerate(self.active):
            if bright <= 0:
                continue
            rect = self.key_rects[i]["rect"].copy()
            rect.x += self.x
            rect.y += self.y
            if self.key_rects[i]["is_white"]:
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                overlay.fill((0, 120, 255, min(180, 80 + bright)))
                surf.blit(overlay, (rect.x, rect.y))

        # 6) Draw overlays for active BLACK keys separately
        for i, bright in enumerate(self.active):
            if bright <= 0:
                continue
            rect = self.key_rects[i]["rect"].copy()
            rect.x += self.x
            rect.y += self.y
            if not self.key_rects[i]["is_white"]:
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                overlay.fill((255, 0, 255, min(180, 80 + bright)))
                surf.blit(overlay, (rect.x, rect.y))

        # 7) Draw only black key outlines on top so overlays remain visible on black keys
        for k in self.key_rects:
            if not k["is_white"]:
                r = k["rect"].copy()
                r.x += self.x
                r.y += self.y
                pygame.draw.rect(surf, GRAY, r, 1)
