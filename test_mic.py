import pyaudio
import time

def find_available_microphone():
    p = pyaudio.PyAudio()
    
    try:
        # Get default microphone index
        default_mic_info = p.get_default_input_device_info()
        default_mic_index = default_mic_info['index']
    except IOError:
        print("No default microphone found.")
        default_mic_index = None

    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    mics = []
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxInputChannels') > 0:
            mics.append(i)
            
    print(f"Found input devices (microphones) at indices: {mics}")
    
    # Reorder so default is checked first
    if default_mic_index is not None and default_mic_index in mics:
        mics.remove(default_mic_index)
        mics.insert(0, default_mic_index)

    active_mic_index = None
    
    for mic_index in mics:
        device_name = p.get_device_info_by_host_api_device_index(0, mic_index).get('name')
        print(f"\nTrying microphone: '{device_name}' (Index: {mic_index})")
        
        try:
            # Try to open the audio stream
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=44100,
                            input=True,
                            input_device_index=mic_index,
                            frames_per_buffer=1024)
            
            print(f"-> Successfully opened stream for: {device_name}")
            
            # Read a small chunk to ensure we can actually get data
            print("-> Testing audio read...")
            data = stream.read(1024, exception_on_overflow=False)
            print("-> Successfully read audio data. This microphone is available!")
            
            # Clean up
            stream.stop_stream()
            stream.close()
            
            active_mic_index = mic_index
            break # Exit the loop, we found a working mic!
            
        except IOError as e:
            # IOError usually means the device is busy, disconnected, or exclusive mode is enabled by another app
            print(f"-> [!] Microphone '{device_name}' is busy or unavailable. Error: {e}")
            print("-> Falling back to the next available microphone...")
            continue
        except Exception as e:
            print(f"-> [!] An unexpected error occurred with '{device_name}': {e}")
            continue
            
    print("\n" + "="*50)
    if active_mic_index is not None:
        device_name = p.get_device_info_by_host_api_device_index(0, active_mic_index).get('name')
        print(f"RESULT: Selected '{device_name}' (Index {active_mic_index}) for listening.")
        p.terminate()
        return active_mic_index
    else:
        print("RESULT: No available microphones could be opened.")
        p.terminate()
        return None

if __name__ == "__main__":
    print("Testing microphones...")
    selected_mic = find_available_microphone()
    
    # Now you can pass `selected_mic` to your speech recognition library
    # For example, with speech_recognition:
    # import speech_recognition as sr
    # if selected_mic is not None:
    #     mic = sr.Microphone(device_index=selected_mic)
    #     with mic as source:
    #         print("Listening...")
