# models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from mido import MidiFile, tempo2bpm

@dataclass
class MidiFileInfo:
    path: Path
    track_count: int
    status: str = "Pending"
    error_message: str = ""

class MidiProcessorModel:
    def __init__(self):
        self.midi_files: Dict[Path, MidiFileInfo] = {}
        self.current_midi: Optional[MidiFile] = None
        self.output_folder: Optional[Path] = None

    def set_output_folder(self, path: Path) -> bool:
        """Add this method to validate output folder"""
        try:
            if not path.exists():
                path.mkdir(parents=True)
            self.output_folder = path
            return True
        except Exception:
            self.output_folder = None
            return False
        
    def get_tempo(self, midi_file_path):
        midi = MidiFile(midi_file_path)
        tempo = None

        for track in midi.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    # Get the tempo in microseconds per beat
                    tempo = msg.tempo
                    # Convert to BPM
                    bpm = tempo2bpm(tempo)
                    return bpm  # Return the first tempo found

        return None  # Return None if no tempo is found


    def add_midi_file(self, path: Path) -> Optional[MidiFileInfo]:
        try:
            midi = MidiFile(path)
            info = MidiFileInfo(path=path, track_count=len(midi.tracks))
            self.midi_files[path] = info
            return info
        except Exception as e:
            return None
    
    def remove_midi_file(self, path: Path) -> None:
        self.midi_files.pop(path, None)
        if self.current_midi and Path(self.current_midi.filename) == path:
            self.current_midi = None
    
    def set_current_midi(self, path: Path) -> Optional[MidiFile]:
        try:
            self.current_midi = MidiFile(path)
            return self.current_midi
        except Exception:
            self.current_midi = None
            return None
    
    def clear_all(self) -> None:
        self.midi_files.clear()
        self.current_midi = None

