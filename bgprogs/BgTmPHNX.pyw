import sys
import os
import datetime
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from HelperPHNX import HandleTimeBasedFunctions


class HandleBgProcess:
    def __init__(self):
        self.tm = HandleTimeBasedFunctions()

    def main(self):
        previous_hour = datetime.datetime.now().hour
        while True:
            self.tm.main_time()
            previous_hour = self.tm.spk_time(previous_hour)

            time.sleep(1)


if __name__ == "__main__":
    bg_process = HandleBgProcess()
    bg_process.main()
