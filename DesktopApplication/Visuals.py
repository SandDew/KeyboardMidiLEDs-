import pygame

class Visuals:
    def __init__(self, keys):
        self.keys = keys

    def draw_keys(self, screen):
        # Draw white keys first
        for key in self.keys:
            if not key.is_black:
                if key.is_pressed:
                    pygame.draw.rect(screen, (0, 255, 255), key.rect)  # Cyan for pressed white keys
                else:
                    pygame.draw.rect(screen, (255, 255, 255), key.rect)  # White
                pygame.draw.rect(screen, (0, 0, 0), key.rect, 2)  # Black border
        
        # Draw black keys on top
        for key in self.keys:
            if key.is_black:
                if key.is_pressed:
                    pygame.draw.rect(screen, (0, 255, 255), key.rect)  # Cyan for pressed black keys
                else:
                    pygame.draw.rect(screen, (0, 0, 0), key.rect)  # Black
                pygame.draw.rect(screen, (100, 100, 100), key.rect, 1)  # Gray border