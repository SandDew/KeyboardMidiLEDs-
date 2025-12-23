from GUI.Main_Window import MidiPlayerGUI


def main():
    last_state = None
    while True:
        app = None
        try:
            app = MidiPlayerGUI(initial_state=last_state)
            app.run()
            break  # normal exit
        except KeyboardInterrupt:
            print("Exiting on user interrupt.")
            break
        except Exception as e:
            print(f"App crashed with error: {e}. Restarting...")
            if app:
                last_state = app.export_state()
            continue
        # If the user requested exit inside the app, stop restarting
        if app and getattr(app, "user_exit", False):
            break


if __name__ == "__main__":
    main()