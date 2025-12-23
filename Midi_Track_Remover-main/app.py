# app.py
import tkinter as tk
from models import MidiProcessorModel
from views import MidiProcessorGUI
from presenters import MidiProcessorPresenter

def main():
    root = tk.Tk()
    model = MidiProcessorModel()
    view = MidiProcessorGUI(root)  # Initialize without presenter
    presenter = MidiProcessorPresenter(model, view)
    view.set_presenter(presenter)  # Use the new set_presenter method
    root.mainloop()

if __name__ == "__main__": 
    main()