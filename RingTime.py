from HelperPhoenix import SpeechEngine

import argparse
from time import sleep


# Open the file in read mode
with open("message.txt", "r") as file:
    message = file.read()

# Now the content of the file is stored in the variable `content`
se = SpeechEngine()
se.speak(message)
sleep(5)
