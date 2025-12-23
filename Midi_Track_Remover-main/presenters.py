import logging
from pathlib import Path
from typing import List, Optional, Protocol, Set
import mido
from mido import MidiFile, MetaMessage
from models import MidiProcessorModel

class MidiProcessorView(Protocol):
    def update_file_list(self, files: List[tuple[Path, int, str]]) -> None: ...
    def update_track_list(self, tracks: List[tuple[int, str, dict]]) -> None: ...
    def update_file_count(self, count: int) -> None: ...
    def update_output_folder(self, path: Optional[Path]) -> None: ...
    def show_error(self, message: str) -> None: ...
    def show_success(self, message: str) -> None: ...

class MidiProcessorPresenter:
    def __init__(self, model: MidiProcessorModel, view: MidiProcessorView):
        self.model = model
        self.view = view
        self.setup_logging()
    
    def setup_logging(self) -> None:
        logging.basicConfig(
            filename="midi_processor.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def add_files(self, file_paths: List[Path]) -> None:
        for path in file_paths:
            info = self.model.add_midi_file(path)
            if info:
                logging.info(f"Added file: {path} with {info.track_count} tracks")
            else:
                msg = f"Error loading file {path}"
                logging.error(msg)
                self.view.show_error(msg)
        
        self._refresh_view()
    
    def remove_files(self, paths: Set[Path]) -> None:
        for path in paths:
            self.model.remove_midi_file(path)
        self._refresh_view()
    
    def set_output_folder(self, path: Optional[Path]) -> None:
        self.model.output_folder = path
        self.view.update_output_folder(path)
    
    def select_file(self, path: Path) -> None:
        midi = self.model.set_current_midi(path)
        if midi:
            tracks_info = self._analyze_tracks(midi.tracks)
            self.view.update_track_list(tracks_info)
        else:
            self.view.show_error(f"Error loading file: {path}")
    
    def process_files(self, selected_tracks: List[int], keep: bool, selected_paths: Optional[Set[Path]] = None) -> None:
        if not self.model.output_folder:
            self.view.show_error("Please set output folder first")
            return
        
        if not selected_tracks:
            self.view.show_error("No tracks selected")
            return
        
        paths_to_process = selected_paths if selected_paths else set(self.model.midi_files.keys())
        
        for path in paths_to_process:
            try:
                midi = MidiFile(path)
                original_tempo = self.model.get_tempo(path)
                if original_tempo is None:
                    original_tempo = 99
                
                new_midi = self._process_tracks(
                    midi,
                    tracks_to_keep=selected_tracks if keep else None,
                    tracks_to_remove=None if keep else selected_tracks
                )
                
                if new_midi:
                    new_midi.tracks[0].append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(original_tempo)))
                    output_path = self.model.output_folder / f"{path.stem}_modified{path.suffix}"
                    new_midi.save(output_path)
                    self.model.midi_files[path].status = "Success"
                    logging.info(f"Successfully processed {path} -> {output_path}")
                else:
                    self.model.midi_files[path].status = "Error: No tracks"
                    logging.error(f"No tracks to process in {path}")
            
            except Exception as e:
                self.model.midi_files[path].status = f"Error: {str(e)}"
                logging.error(f"Error processing {path}: {e}")
        
        self._refresh_view()
        self.view.show_success("Processing complete. Check log file for details.")
    
    def clear_all(self) -> None:
        self.model.clear_all()
        self._refresh_view()
    
    def _refresh_view(self) -> None:
        files = [(info.path, info.track_count, info.status) 
                for info in self.model.midi_files.values()]
        self.view.update_file_list(files)
        self.view.update_file_count(len(files))
        
        if not self.model.current_midi:
            self.view.update_track_list([])
    
    @staticmethod
    def _analyze_tracks(tracks):
        track_info = []
        for i, track in enumerate(tracks):
            track_name = "Unnamed"
            msg_types = {}
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                msg_types[msg.type] = msg_types.get(msg.type, 0) + 1
            track_info.append((i, track_name, msg_types))
        return track_info
    
    @staticmethod
    def _process_tracks(midi: MidiFile, 
                       tracks_to_keep: Optional[List[int]] = None,
                       tracks_to_remove: Optional[List[int]] = None) -> Optional[MidiFile]:
        if tracks_to_keep is not None:
            selected_tracks = tracks_to_keep
            keep = True
        else:
            selected_tracks = tracks_to_remove
            keep = False
        
        new_midi = MidiFile(ticks_per_beat=midi.ticks_per_beat)
        
        for i, track in enumerate(midi.tracks):
            if (keep and i in selected_tracks) or (not keep and i not in selected_tracks):
                new_midi.tracks.append(track)
        
        return new_midi if new_midi.tracks else None
