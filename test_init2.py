from Utils.limbs.assistant_io import SpeechEngine
import traceback
try:
    e = SpeechEngine()
    e.speak('test')
    print('Speech completed.')
except Exception as ex:
    traceback.print_exc()
