from Utils.limbs.assistant_io import SpeechEngine
import traceback
try:
    e = SpeechEngine()
    print('Voice ID:', e.voice_id)
    e.speak('test')
except Exception as ex:
    traceback.print_exc()
