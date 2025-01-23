import os
import sys
import subprocess
import pyautogui as pg
from time import sleep
from helpers.UtilitiesPHNX import Utility
from helpers.HelperPHNX import VoiceAssistantGUI, VoiceRecognition, SpeechEngine
import tkinter as tk
from datetime import datetime

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


def load_phnx():
    sleep(3)
    paths = [
        "C:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgBtryPHNX.pyw",
        "C:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgTmPHNX.pyw",
        "C:\\STDY\\GIT_PROJECTS\\Phoenix\\batch\\main.bat",
    ]
    ct = 0
    for path in paths:
        if ct == 2:
            utils.desKtoP(4)
        os.startfile(path)
        sleep(10)
        ct += 1


def terminate_background_processes():
    try:
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
        sleep(5)
        main()


if __name__ == "__main__":
    main()
    sys.exit()
