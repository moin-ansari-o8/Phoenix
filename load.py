import os
import sys
import subprocess
import pyautogui as pg
from time import sleep
from helpers.UtilitiesPHNX import Utility
from helpers.HelperPHNX import VoiceAssistantGUI, VoiceRecognition, SpeechEngine
import tkinter as tk
from datetime import datetime
import keyboard

root = tk.Tk()
gui = VoiceAssistantGUI(root)
recog = VoiceRecognition(gui)
spk = SpeechEngine()
utils = Utility(reco=recog, spk=spk)


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


def launch_in_bg(file_path):
    if not os.path.isfile(file_path):
        print(f"⛔ File not found: {file_path}")
        return

    if not file_path.endswith(".pyw"):
        print(f"⚠️ Not a .pyw file: {file_path}")
        return

    try:
        subprocess.Popen(["pythonw", file_path], shell=True)
        print(f"✅ Launched in bg: {os.path.basename(file_path)}")
    except Exception as e:
        print(f"❌ Failed to launch {file_path}: {e}")


def load_phnx():
    # sleep(3)
    paths = [
        "C:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgBtryPHNX.pyw",
        "C:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgTmPHNX.pyw",
        # "C:\\STDY\\GIT_PROJECTS\\Phoenix\\batch\\main.bat",
    ]
    for path in paths:
        launch_in_bg(path)
        sleep(0.5)
    utils.desKtoP(4)
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
        subprocess.run(["taskkill", "/F", "/IM", "pyw.exe"], check=True)
        print("<=>")
    except subprocess.CalledProcessError:
        print("<!>")
    except Exception as e:
        print(f"<!>")


def main():
    try:
        terminate_background_processes()
        startup_phnx()
        load_phnx()
    except Exception as e:
        print(f"An error occurred: {e}")
        sleep(1)
        main()


if __name__ == "__main__":
    main()
    sys.exit(0)
