# views.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Set, Protocol
from pathlib import Path

class PresenterProtocol(Protocol):
    def add_files(self, file_paths: List[Path]) -> None: ...
    def clear_all(self) -> None: ...
    def select_file(self, path: Path) -> None: ...
    def set_output_folder(self, path: Optional[Path]) -> None: ...
    def process_files(self, selected_tracks: List[int], keep: bool, selected_paths: Optional[Set[Path]] = None) -> None: ...

class MidiProcessorGUI(tk.Frame):
    def __init__(self, master: tk.Tk, presenter: Optional[PresenterProtocol] = None):
        super().__init__(master)
        self.presenter = presenter
        self.track_vars: Dict[int, tk.BooleanVar] = {}
        
        self.master.title("MIDI Track Processor")
        self.master.geometry("1000x800")
        
        self._create_widgets()
        self.grid(sticky=(tk.W, tk.E, tk.N, tk.S))

    def set_presenter(self, presenter: PresenterProtocol) -> None:
        """Set the presenter after initialization"""
        self.presenter = presenter
        self._update_commands()

    def _ensure_presenter(self, method_name: str) -> None:
        """Ensure presenter exists before calling methods"""
        if self.presenter is None:
            messagebox.showerror("Error", f"Cannot {method_name}: Presenter not initialized")
            raise RuntimeError("Presenter not initialized")

    def _create_widgets(self):
        # File selection frame
        file_frame = ttk.LabelFrame(self, text="File Selection", padding="5")
        file_frame.grid(row=0, sticky=(tk.W, tk.E), pady=5)
        
        # Create buttons without commands initially
        self.select_files_btn = ttk.Button(file_frame, text="Select Files")
        self.select_files_btn.grid(row=0, column=0, padx=5)
        
        self.select_folder_btn = ttk.Button(file_frame, text="Select Folder")
        self.select_folder_btn.grid(row=0, column=1, padx=5)
        
        self.set_output_btn = ttk.Button(file_frame, text="Set Output Folder")
        self.set_output_btn.grid(row=0, column=2, padx=5)
        
        self.output_label = ttk.Label(file_frame, text="Output folder: Not set")
        self.output_label.grid(row=0, column=3, padx=5)

        # Buttons frame
        buttons_frame = ttk.LabelFrame(self, text="Actions", padding="5")
        buttons_frame.grid(row=1, sticky=(tk.W, tk.E), pady=5)
        
        self.keep_tracks_btn = ttk.Button(buttons_frame, text="Keep Selected Tracks")
        self.keep_tracks_btn.grid(row=0, column=0, padx=5)
        
        self.remove_tracks_btn = ttk.Button(buttons_frame, text="Remove Selected Tracks")
        self.remove_tracks_btn.grid(row=0, column=1, padx=5)
        
        self.clear_all_btn = ttk.Button(buttons_frame, text="Clear All")
        self.clear_all_btn.grid(row=0, column=2, padx=5)
        
        # Files list frame
        files_frame = ttk.LabelFrame(self, text="Selected Files", padding="5")
        files_frame.grid(row=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value="Files: 0")
        ttk.Label(files_frame, textvariable=self.status_var).grid(row=0, sticky=tk.W)
        
        self.files_tree = ttk.Treeview(
            files_frame,
            columns=("path", "tracks", "status"),
            show="headings",
            selectmode='extended'
        )
        self.files_tree.heading("path", text="File Path")
        self.files_tree.heading("tracks", text="Track Count")
        self.files_tree.heading("status", text="Status")
        
        self.files_tree.column("path", width=400)
        self.files_tree.column("tracks", width=100)
        self.files_tree.column("status", width=100)
        
        self.files_tree.grid(row=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tracks frame
        tracks_frame = ttk.LabelFrame(self, text="Track Information", padding="5")
        tracks_frame.grid(row=3, sticky=(tk.W, tk.E), pady=5)

        # Create a canvas for the scrollable area without a fixed height
        self.track_canvas = tk.Canvas(tracks_frame)
        self.track_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create a vertical scrollbar for the canvas
        self.track_scrollbar = ttk.Scrollbar(tracks_frame, orient="vertical", command=self.track_canvas.yview)
        self.track_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure the canvas to use the scrollbar
        self.track_canvas.configure(yscrollcommand=self.track_scrollbar.set)

        # Create a frame inside the canvas to hold the track information
        self.scrollable_frame = ttk.Frame(self.track_canvas)
        self.track_canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

        # Bind the frame's configuration to the canvas
        self.scrollable_frame.bind("<Configure>", lambda e: self.track_canvas.configure(scrollregion=self.track_canvas.bbox("all")))

        # Configure the grid weights to allow expansion
        tracks_frame.grid_rowconfigure(0, weight=1)  # Allow the canvas to expand
        tracks_frame.grid_columnconfigure(0, weight=1)  # Allow the canvas to expand

        self.files_tree.bind("<Button-1>", self._on_tree_click)  # Bind click event

    def _update_commands(self):
        """Update button commands after presenter is set"""
        self.select_files_btn.config(command=self._browse_files)
        self.select_folder_btn.config(command=self._browse_folder)  # This needs implementation
        self.set_output_btn.config(command=self._set_output_folder)
        self.keep_tracks_btn.config(command=lambda: self._process_files(True))
        self.remove_tracks_btn.config(command=lambda: self._process_files(False))
        self.clear_all_btn.config(command=lambda: self.presenter.clear_all() if self.presenter else None)
        self.files_tree.bind('<<TreeviewSelect>>', self._on_file_select)

    def _browse_files(self):
        self._ensure_presenter("browse files")
        files = filedialog.askopenfilenames(
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        if files:
            self.presenter.add_files([Path(f) for f in files])

    def _browse_folder(self):
        """Add method to handle folder selection"""
        self._ensure_presenter("browse folder")
        folder = filedialog.askdirectory()
        if folder:
            folder_path = Path(folder)
            midi_files = list(folder_path.glob("*.mid")) + list(folder_path.glob("*.midi"))
            if midi_files:
                self.presenter.add_files(midi_files)
            else:
                self.show_error("No MIDI files found in selected folder")
                    
    def _set_output_folder(self):
        self._ensure_presenter("set output folder")  # Add this line
        folder = filedialog.askdirectory()
        if folder:
            self.presenter.set_output_folder(Path(folder))
    
    def _on_file_select(self, event):
        self._ensure_presenter("select file")  # Add this line
        selection = self.files_tree.selection()
        if selection:
            path = Path(self.files_tree.item(selection[-1])["values"][0])
            self.presenter.select_file(path)
    
    def _process_files(self, keep: bool):
        self._ensure_presenter("process files")  # Ensure presenter is set
        selected_tracks = [i for i, var in self.track_vars.items() if var.get()]
        
        if not selected_tracks:
            self.show_error("No tracks selected")
            return
        
        # Prepare confirmation message
        if keep:
            track_indices = ', '.join(map(str, selected_tracks))
            confirmation_message = f"You will keep only these tracks: {track_indices}. Do you want to proceed?"
        else:
            track_indices = ', '.join(map(str, selected_tracks))
            confirmation_message = f"You are about to remove these tracks: {track_indices}. Do you want to proceed?"

        # Show confirmation dialog
        if messagebox.askokcancel("Confirm Action", confirmation_message):
            selected_items = self.files_tree.selection()
            selected_paths = {Path(self.files_tree.item(item)["values"][0]) 
                              for item in selected_items} if selected_items else None
            
            self.presenter.process_files(selected_tracks, keep, selected_paths)
        else:
            # User canceled the action
            return
    
    # View interface implementation
    def update_file_list(self, files: List[tuple[Path, int, str]]) -> None:
        self.files_tree.delete(*self.files_tree.get_children())
        for path, track_count, status in files:
            self.files_tree.insert("", "end", values=(str(path), track_count, status))
    
    def update_track_list(self, tracks: List[tuple[int, str, dict]]) -> None:
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.track_vars.clear()
        
        for i, name, msg_types in tracks:
            self.track_vars[i] = tk.BooleanVar()
            ttk.Checkbutton(
                self.scrollable_frame,
                variable=self.track_vars[i]
            ).grid(row=i, column=0, padx=5)
            
            track_info = f"Track {i}: {name}\n"
            track_info += f"Messages: {sum(msg_types.values())}\n"
            track_info += f"Types: {', '.join(f'{k}: {v}' for k, v in msg_types.items())}"
            
            ttk.Label(
                self.scrollable_frame,
                text=track_info,
                justify=tk.LEFT
            ).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
    
    def update_file_count(self, count: int) -> None:
        self.status_var.set(f"Files: {count}")
    
    def update_output_folder(self, path: Optional[Path]) -> None:
        self.output_label.config(
            text=f"Output folder: {path}" if path else "Output folder: Not set"
        )
    
    def show_error(self, message: str) -> None:
        tk.messagebox.showerror("Error", message)
    
    def show_success(self, message: str) -> None:
        tk.messagebox.showinfo("Success", message)

    def _on_tree_click(self, event):
        """Deselect files when clicking on an empty area of the treeview."""
        # Get the region of the click
        region = self.files_tree.identify_region(event.x, event.y)
        if region == "heading" or region == "cell":
            # If the click is on the heading or a cell, do nothing
            return
        # Clear selection if clicked on an empty area
        self.files_tree.selection_remove(*self.files_tree.selection())
