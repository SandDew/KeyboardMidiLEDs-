import mido
from Config import MIDI_KEY_OFFSET, NUM_KEYS

def parse_midi_file(midi_file_path):
    """Parse MIDI file and extract note intervals (start, end) for each key."""
    try:
        mid = mido.MidiFile(midi_file_path)
        note_times = [[] for _ in range(NUM_KEYS)]  # Each entry: list of (start, end)
        abs_time = 0
        note_on_dict = {}

        for msg in mid:
            abs_time += msg.time
            if msg.type == 'note_on':
                key = msg.note - MIDI_KEY_OFFSET
                if 0 <= key < NUM_KEYS:
                    if msg.velocity > 0:
                        # Note ON
                        note_on_dict.setdefault(key, []).append(abs_time)
                    else:
                        # Note OFF (note_on with velocity 0)
                        if key in note_on_dict and note_on_dict[key]:
                            start_time = note_on_dict[key].pop(0)
                            note_times[key].append((start_time, abs_time))
            elif msg.type == 'note_off':
                key = msg.note - MIDI_KEY_OFFSET
                if 0 <= key < NUM_KEYS:
                    if key in note_on_dict and note_on_dict[key]:
                        start_time = note_on_dict[key].pop(0)
                        note_times[key].append((start_time, abs_time))

        # Handle any notes that didn't get a note_off (sustain to end)
        for key in range(NUM_KEYS):
            while note_on_dict.get(key):
                start_time = note_on_dict[key].pop(0)
                note_times[key].append((start_time, abs_time))

        return note_times, mid.length
    except Exception as e:
        raise Exception(f"Error parsing MIDI: {e}")