import os
import sys
import subprocess
import pyautogui as pg
from time import sleep
from Utils.limbs.action_utilities import Utility
from Utils.limbs.assistant_io import (
    VoiceAssistantGUI,
    VoiceRecognition,
    SpeechEngine,
)
import tkinter as tk
from datetime import datetime
import keyboard

root = tk.Tk()
gui = VoiceAssistantGUI(root)
recog = VoiceRecognition(gui)
spk = SpeechEngine()
utils = Utility(spk=spk, reco=recog)


def startup_phnx():
    hour = datetime.now().hour
    # time.sleep(15)
    utils.intrOmsC()
    utils.speak(utils.onL())
    # utils.speak("Let me setup your desktops... until then... sit back and enjoy the music!")
    # utils.rockMsc(0.5)
    if hour < 12:
        utils.speak(utils.greet("Morning"))
    elif 12 <= hour <= 17:
        utils.speak(utils.greet("Afternoon"))
    else:
        utils.speak(utils.greet("Evening"))

    utils.speak(utils.phN())


import os
import subprocess


def launch_in_bg(file_path):
    if not os.path.isfile(file_path):
        print(f"⛔ File not found: {file_path}")
        return

    ext = os.path.splitext(file_path)[1].lower()

    # Use venv python
    venv_python = os.path.join(
        os.path.dirname(__file__), ".venv", "Scripts", "python.exe"
    )
    venv_pythonw = os.path.join(
        os.path.dirname(__file__), ".venv", "Scripts", "pythonw.exe"
    )

    try:
        if ext == ".pyw":
            subprocess.Popen([venv_pythonw, file_path])
            print(f"✅ Launched .pyw in bg: {os.path.basename(file_path)}")
        elif ext == ".py":
            subprocess.Popen([venv_python, file_path])
            print(f"✅ Launched .py in bg: {os.path.basename(file_path)}")
        elif ext == ".bat":
            subprocess.Popen(["cmd.exe", "/c", file_path], shell=True)
            print(f"✅ Launched .bat in bg: {os.path.basename(file_path)}")
        else:
            print(f"⚠️ Unsupported file type: {file_path}")
    except Exception as e:
        print(f"❌ Failed to launch {file_path}: {e}")


def load_phnx():
    # sleep(3)
    paths = [
        "C:\\STDY\\MYAIS\\Phoenix\\bgprogs\\battery_monitor.pyw",
        "C:\\STDY\\MYAIS\\Phoenix\\bgprogs\\time_monitor.pyw",
        # "C:\\STDY\\MYAIS\\Phoenix\\batch\\main.bat",
    ]
    for path in paths:
        launch_in_bg(path)
        sleep(0.5)
    utils.desKtoP(1)
    pg.keyDown("win")
    pg.press("r")
    pg.keyUp("win")
    keyboard.write("phoenix main")
    pg.press("enter")
    sleep(2)
    sys.exit(0)


def terminate_background_processes():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "pythonw3.11.exe"], check=True)
        print("<=>")
    except subprocess.CalledProcessError:
        print("<!>")
    except Exception as e:
        print(f"<!>")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"], check=True)
        print("<=>")
    except subprocess.CalledProcessError:
        print("<!>")
    except Exception as e:
        print(f"<!>")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "pyw.exe"], check=True)
        print("<=>")
    except subprocess.CalledProcessError:
        print("<!>")
    except Exception as e:
        print(f"<!>")


def main():
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            terminate_background_processes()
            startup_phnx()
            load_phnx()
            break  # Success, exit loop
        except KeyboardInterrupt:
            print("\n\nPhoenix startup cancelled by user.")
            sys.exit(0)
        except Exception as e:
            retry_count += 1
            print(
                f"An error occurred during startup (attempt {retry_count}/{max_retries}): {e}"
            )
            if retry_count < max_retries:
                print(f"Retrying in 2 seconds...")
                sleep(2)
            else:
                print("\nFailed to start Phoenix after multiple attempts.")
                print("Please check:")
                print("1. Python environment is properly configured")
                print("2. All dependencies are installed")
                print("3. Background processes are not conflicting")
                import traceback

                traceback.print_exc()
                sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(0)
