import os
import sys
import subprocess
import pyautogui as pg
from time import sleep
from HelperPHNX import Utility
from datetime import datetime

utils = Utility()

btry_check = os.path.join(os.path.dirname(__file__), "data", "intents.json")


def startup_phnx():
    hour = datetime.now().hour
    # time.sleep(15)
    utils.intrOmsC()
    utils.speak(utils.onL())
    utils.speak(utils.phN())
    # utils.speak("Let me setup your desktops... until then... sit back and enjoy the music!")
    # utils.rockMsc(0.5)
    if hour < 12:
        utils.speak(utils.greet("Morning"))
    elif 12 <= hour <= 17:
        utils.speak(utils.greet("Afternoon"))
    else:
        utils.speak(utils.greet("Evening"))


def load_phnx():
    sleep(3)
    paths = [
        "E:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgBtryPHNX.pyw",
        "E:\\STDY\\GIT_PROJECTS\\Phoenix\\bgprogs\\BgTmPHNX.pyw",
        "E:\\STDY\\GIT_PROJECTS\\Phoenix\\batch\\main.bat",
    ]
    ct = 0
    for path in paths:
        if ct == 2:
            utils.desKtoP(3)
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
