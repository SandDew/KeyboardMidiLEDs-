# MIDI Processor

A MIDI Processor application that allows users to manage and manipulate MIDI files. This application provides functionalities to add, remove, and process MIDI files, as well as to set output folders and manage track information.

## Features

- Add MIDI files from the file system.
- Select and manage multiple MIDI files.
- Set an output folder for processed MIDI files.
- Keep or remove selected tracks from MIDI files.
- Display track information and status.

## Requirements

- Python 3.7 or higher
- Required Python packages:
  - `mido`
  - `tkinter` (comes pre-installed with Python)
  - `dataclasses` (for Python 3.6 and lower)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/essamsoft/midi-processor.git
   cd Midi_Track_Remover
   ```

2. **Create a virtual environment (optional but recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required packages:**

   ```bash
   pip install mido
   ```

4. **Run the application:**

   You can run the application by executing the following command:

   ```bash
   python main.py  # Replace with the actual entry point of your application
   ```

## Usage

1. Launch the application.
2. Use the "Select Files" button to add MIDI files.
3. Use the "Select Folder" button to add all MIDI files from a directory.
4. Set the output folder where processed MIDI files will be saved.
5. Select tracks to keep or remove using checkboxes.
6. Click the "Keep Selected Tracks" or "Remove Selected Tracks" button to process the files.
7. The status of the files will be displayed in the application.

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Mido](https://mido.readthedocs.io/en/latest/) for MIDI file handling.
- [Tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI framework.