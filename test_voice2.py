import pyttsx3
import pythoncom
def test_voice():
    pythoncom.CoInitialize()
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    print('idx 1 voice:', voices[1].id)
    engine.setProperty('voice', voices[1].id)
    engine.say('Hello from zira with com')
    engine.runAndWait()
import threading
t = threading.Thread(target=test_voice)
t.start()
t.join()
