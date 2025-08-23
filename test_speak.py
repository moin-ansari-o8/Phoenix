import pyttsx3

engine = pyttsx3.init("sapi5")
engine.say("Hello from command prompt")
engine.runAndWait()
