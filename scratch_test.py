import threading
import pyttsx3
def test():
    try:
        engine = pyttsx3.init('sapi5')
        engine.setProperty('voice', engine.getProperty('voices')[1].id)
        engine.say('Thread test')
        engine.runAndWait()
    except Exception as e:
        print('Error:', e)

t = threading.Thread(target=test)
t.start()
t.join()
