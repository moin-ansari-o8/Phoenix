import os
import sys
import threading
from time import sleep
import random
import pyttsx3
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk
from time import sleep
from colorama import Fore
import warnings
import numpy as np
import pyaudio
import queue
import time
import asyncio
from datetime import datetime

# Suppress pygame deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

# Hide pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Edge TTS for natural voice (like IGRS)
try:
    import edge_tts
    import pygame

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("[Warning] edge-tts or pygame not installed. Using pyttsx3 fallback.")

# Faster-Whisper for offline speech recognition
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print(
        "[Warning] faster-whisper not installed. Using Google Speech Recognition (requires internet)."
    )

# VAD (Voice Activity Detection) for continuous listening
try:
    import webrtcvad

    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("[Warning] webrtcvad not installed. Install with: pip install webrtcvad")


class SpeechEngine:
    """
    Speech Engine using Edge TTS (natural neural voices) with pyttsx3 fallback.
    Edge TTS provides much more natural-sounding voices like IGRS.
    """
    
    # Neural voice options - pick your favorite!
    # Male: en-US-GuyNeural, en-US-ChristopherNeural, en-GB-RyanNeural, en-AU-WilliamNeural
    # Female: en-US-JennyNeural, en-US-AriaNeural, en-GB-SoniaNeural
    EDGE_VOICE = "en-US-ChristopherNeural"  # Natural male voice
    EDGE_PITCH = "+0Hz"  # Adjust pitch: "+5Hz", "-5Hz", etc.
    EDGE_RATE = "+10%"   # Slightly faster speech
    
    def __init__(self):
        self.lock = threading.Lock()
        self.honorifics = True
        self.use_edge_tts = EDGE_TTS_AVAILABLE
        self._pygame_initialized = False
        
        # Temp file for Edge TTS audio
        self._temp_audio_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self._temp_audio_dir, exist_ok=True)
        self._temp_audio_file = os.path.join(self._temp_audio_dir, "phoenix_speech.mp3")
        
        if self.use_edge_tts:
            print(f"🎤 Voice Engine: Edge TTS ({self.EDGE_VOICE})")
        
        # Fallback: pyttsx3 settings
        self.voice_id = None
        self.rate = 174
        self.volume = 1.0
        
        if not self.use_edge_tts:
            try:
                temp_engine = pyttsx3.init("sapi5")
                voices = temp_engine.getProperty("voices")
                if voices and len(voices) > 1:
                    self.voice_id = voices[1].id
                temp_engine.stop()
                del temp_engine
                print("🎤 Voice Engine: pyttsx3 (SAPI5)")
            except Exception:
                pass

    def _manage_honorifics(self):
        self.honorifics = False
        sleep(30)
        self.honorifics = True
    
    def _apply_honorifics(self, audio):
        """Replace 'sir' with random honorifics for personality"""
        replacements = [
            "boss", "captain", "commander", "my lord", "your majesty",
            "my liege", "your grace", "sir", "boss", "master", "sensei",
        ]
        
        for punctuation in ["", "?", "!", ".", " "]:
            if f" sir{punctuation}" in audio:
                if self.honorifics:
                    replacement = random.choice(replacements)
                    audio = audio.replace(f"sir{punctuation}", f"{replacement}{punctuation}")
                    threading.Thread(target=self._manage_honorifics).start()
                    break
                else:
                    audio = audio.replace(f"sir{punctuation}", "")
        return audio
    
    def _init_pygame(self):
        """Initialize pygame mixer if not already done"""
        if not self._pygame_initialized:
            try:
                pygame.mixer.init()
                self._pygame_initialized = True
            except Exception as e:
                print(f"⚠️ Pygame init failed: {e}")
                return False
        return True
    
    def _cleanup_pygame(self):
        """Cleanup pygame mixer after playback"""
        try:
            pygame.mixer.music.unload()
        except:
            pass
    
    def _generate_and_play_edge_tts(self, text):
        """Generate and play speech using Edge TTS (synchronous wrapper)"""
        try:
            # Initialize pygame if needed
            if not self._init_pygame():
                return False
            
            # Cleanup any previous audio
            self._cleanup_pygame()
            
            # Remove old file if exists
            if os.path.exists(self._temp_audio_file):
                try:
                    os.remove(self._temp_audio_file)
                except:
                    pass
            
            # Generate speech with Edge TTS using a new event loop
            async def generate():
                communicate = edge_tts.Communicate(
                    text, 
                    self.EDGE_VOICE, 
                    pitch=self.EDGE_PITCH, 
                    rate=self.EDGE_RATE
                )
                await communicate.save(self._temp_audio_file)
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(generate())
            finally:
                loop.close()
            
            # Play the audio
            if os.path.exists(self._temp_audio_file):
                pygame.mixer.music.load(self._temp_audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                self._cleanup_pygame()
                return True
            return False
            
        except Exception as e:
            print(f"⚠️ Edge TTS error: {e}")
            return False
    
    def speak(self, audio, speed=174):
        """
        Thread-safe method to handle text-to-speech.
        Uses Edge TTS (neural voice) with pyttsx3 fallback.
        Sets speaking state for self-voice suppression.
        """
        # Import here to avoid circular imports
        from helpers.ConsoleUI import phoenix_said, print_block
        
        # Speaking state file for cross-process communication
        speaking_file = os.path.join(os.path.dirname(__file__), "..", ".speaking")
        
        try:
            # Mark as speaking (create lock file)
            with open(speaking_file, "w") as f:
                f.write(str(time.time()))
            
            with self.lock:
                # Apply personality (honorifics replacement)
                audio = self._apply_honorifics(audio)
                phoenix_said(audio)  # TUI output
                
                # Try Edge TTS first (natural voice)
                if self.use_edge_tts:
                    if self._generate_and_play_edge_tts(audio):
                        # Remove speaking flag after speech + buffer
                        sleep(0.5)
                        try:
                            os.remove(speaking_file)
                        except:
                            pass
                        return
                    print_block("⚠️  Edge TTS failed, using fallback voice...")
                
                # Fallback to pyttsx3
                self._speak_pyttsx3(audio, speed)
                
        except Exception as e:
            print_block(f"⚠️  Speech error: {e}")
        finally:
            # Always clean up speaking flag
            sleep(0.5)  # Buffer time after speech
            try:
                os.remove(speaking_file)
            except:
                pass
    
    def _speak_pyttsx3(self, audio, speed=174):
        """Fallback speech using pyttsx3"""
        try:
            engine = pyttsx3.init("sapi5")
        except Exception:
            try:
                engine = pyttsx3.init()
            except Exception:
                return
        
        try:
            if self.voice_id:
                engine.setProperty("voice", self.voice_id)
            engine.setProperty("rate", speed)
            engine.setProperty("volume", self.volume)
        except:
            pass
        
        engine.say(audio)
        engine.runAndWait()
        engine.stop()
        del engine
        sleep(0.2)

    def threadedSpeak(self, audio):
        """
        Starts a thread to call the `speak` method.
        """
        threading.Thread(target=self.speak, args=(audio,)).start()


class VoiceAssistantGUI:

    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.attributes("-topmost", True)
        self.setup_transparency()
        self.mic_label = tk.Label(self.root, bg="white")
        self.mic_label.pack()
        self.listen_img_path = os.path.join(
            os.path.dirname(__file__), "..", "assets", "img", "green.png"
        )
        self.recognize_img_path = os.path.join(
            os.path.dirname(__file__), "..", "assets", "img", "red.png"
        )
        if not os.path.exists(self.listen_img_path):
            print("Error: Listen image not found!")
        if not os.path.exists(self.recognize_img_path):
            print("Error: Recognize image not found!")
        self.listen_img = Image.open(self.listen_img_path)
        self.recognize_img = Image.open(self.recognize_img_path)
        max_width = max(4, 4)
        max_height = max(30, 30)
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def hide_listen_image(self):
        self.mic_label.config(image=None)

    def hide_recognize_image(self):
        self.mic_label.config(image=None)

    def setup_transparency(self):
        if self.root.tk.call("tk", "windowingsystem") == "win32":
            self.root.attributes("-topmost", 1)
        elif self.root.tk.call("tk", "windowingsystem") == "x11":
            self.root.attributes("-type", "dock")
        elif self.root.tk.call("tk", "windowingsystem") == "aqua":
            self.root.call(
                "::tk::unsupported::MacWindowStyle",
                "style",
                self.root._w,
                "help",
                "none",
            )
        self.root.wm_attributes("-transparentcolor", "white")

    def show_listen_image(self):
        self.mic_label.config(image=None)
        mic_img = Image.open(self.listen_img_path).convert("RGBA")
        mic_img = mic_img.resize((40, 40), Image.LANCZOS)
        mic_img = ImageTk.PhotoImage(mic_img)  # Convert to Tkinter-compatible image
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img  # Keep a reference to the image object
        self.root.update()

    def show_recognize_image(self):
        self.mic_label.config(image=None)
        recognize_img = self.recognize_img.resize((40, 40), Image.LANCZOS).convert(
            "RGBA"
        )
        recognize_img = ImageTk.PhotoImage(recognize_img)
        self.mic_label.config(image=recognize_img)
        self.mic_label.image = recognize_img  # Keep a reference to the image object
        self.root.update()


class VoiceRecognition:

    def __init__(self, gui):
        self.gui = gui
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1

        # Audio settings for continuous listening
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.CHANNELS = 1

        # VAD settings
        self.MIN_SILENCE_DURATION = 0.8  # Seconds of silence to trigger processing
        self.MIN_SPEECH_DURATION = 0.3  # Minimum speech duration
        self.ENERGY_THRESHOLD = 150  # RMS energy threshold (raised for fan noise)
        self.SPEECH_CONFIRMATION_CHUNKS = (
            3  # Require N consecutive chunks to confirm speech
        )
        self.MAX_SPEECH_DURATION = 30.0  # Max seconds before auto-processing

        # State management
        self.audio_buffer = []
        self.is_speaking = False
        self.silence_start_time = None
        self.speech_start_time = None
        self.consecutive_speech_chunks = 0  # Track consecutive speech detections
        self.consecutive_silence_chunks = 0  # Track consecutive silence detections

        # Initialize VAD
        self.vad = None
        if VAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad()
                self.vad.set_mode(3)  # Most aggressive (human voice only)
            except Exception as e:
                print(f"⚠️ VAD init failed: {e}")
                self.vad = None

        # Initialize Faster-Whisper for offline recognition
        # Using CUDA/GPU for 5-10x faster transcription!
        self.whisper_model = None
        if WHISPER_AVAILABLE:
            try:
                # Try CUDA (GPU) first for maximum speed
                try:
                    import torch
                    cuda_available = torch.cuda.is_available()
                except ImportError:
                    cuda_available = False
                
                if cuda_available:
                    print("🚀 Loading Whisper on GPU (CUDA)...")
                    self.whisper_model = WhisperModel(
                        "small", device="cuda", compute_type="float16"
                    )
                    print("✅ Speech recognition ready (GPU accelerated)")
                else:
                    print("💻 Loading Whisper on CPU...")
                    self.whisper_model = WhisperModel(
                        "small", device="cpu", compute_type="int8"
                    )
                    print("✅ Speech recognition ready (CPU mode)")
            except Exception as e:
                print(f"⚠️ Whisper load failed: {e}")
                print("⚠️ Using Google Speech (requires internet)")

    def _detect_speech(self, audio_chunk):
        """Detect if audio chunk contains speech using VAD and/or energy"""
        # Energy-based detection
        if len(audio_chunk) > 0:
            rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
            has_energy = rms > self.ENERGY_THRESHOLD
        else:
            has_energy = False

        # VAD-based detection
        has_vad_speech = False
        if self.vad is not None:
            try:
                # VAD needs 10, 20, or 30ms frames
                frame_duration_ms = 20
                samples_per_frame = int(self.SAMPLE_RATE * frame_duration_ms / 1000)
                audio_bytes = audio_chunk.tobytes()

                # Check multiple frames
                for i in range(0, len(audio_bytes), samples_per_frame * 2):
                    frame = audio_bytes[i : i + samples_per_frame * 2]
                    if len(frame) == samples_per_frame * 2:
                        if self.vad.is_speech(frame, self.SAMPLE_RATE):
                            has_vad_speech = True
                            break
            except Exception as e:
                # Silently ignore VAD errors
                pass

        # Combine both methods (OR logic)
        result = has_energy or has_vad_speech

        # Show when speech starts (once per utterance)
        if result and not self.is_speaking:
            print("🎙️ Voice detected...")

        return result

    def take_command(self):
        """Continuous listening with VAD-based speech detection"""
        # Use Whisper continuous mode if available
        if self.whisper_model is not None:
            return self._continuous_listen_whisper()
        else:
            # Fallback to old speech_recognition method
            return self._fallback_listen()

    def _continuous_listen_whisper(self):
        """Continuous listening with Faster-Whisper (no timeouts)"""
        print("\n🎧 Listening... (speak naturally, pause when done)")
        try:
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE,
            )

            self.gui.show_listen_image()

            # Reset state
            self.audio_buffer = []
            self.is_speaking = False
            self.silence_start_time = None
            self.speech_start_time = None
            self.consecutive_speech_chunks = 0
            self.consecutive_silence_chunks = 0

            chunk_count = 0
            # Continuous listening loop
            while True:
                # Read audio chunk
                audio_data = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(audio_data, dtype=np.int16)
                chunk_count += 1

                # Detect speech
                has_speech = self._detect_speech(audio_chunk)
                current_time = time.time()

                # Update consecutive counters
                if has_speech:
                    self.consecutive_speech_chunks += 1
                    self.consecutive_silence_chunks = 0
                else:
                    self.consecutive_silence_chunks += 1
                    self.consecutive_speech_chunks = 0

                # Require multiple consecutive chunks to confirm speech/silence
                confirmed_speech = (
                    self.consecutive_speech_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )
                confirmed_silence = (
                    self.consecutive_silence_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )

                if confirmed_speech:
                    # Confirmed speech detected
                    if not self.is_speaking:
                        # Speech just started
                        self.is_speaking = True
                        self.speech_start_time = current_time
                        self.audio_buffer = []
                        self.silence_start_time = None  # Reset silence timer

                    # Add to buffer
                    self.audio_buffer.append(audio_chunk)

                    # Check if speech duration exceeded max
                    speech_duration_so_far = current_time - self.speech_start_time
                    if speech_duration_so_far >= self.MAX_SPEECH_DURATION:
                        print("⏱️ Max duration reached, processing...")
                        stream.stop_stream()
                        stream.close()
                        audio.terminate()

                        self.gui.show_recognize_image()
                        print("🧠 Processing speech...")
                        result = self._transcribe_buffer()
                        self.gui.hide_listen_image()
                        return result

                elif confirmed_silence and self.is_speaking:
                    # Confirmed silence during speech
                    if self.silence_start_time is None:
                        self.silence_start_time = current_time

                    # Continue buffering
                    self.audio_buffer.append(audio_chunk)

                    # Check if silence duration exceeded threshold
                    silence_duration = current_time - self.silence_start_time
                    if silence_duration >= self.MIN_SILENCE_DURATION:
                        # Silence long enough, process the speech
                        stream.stop_stream()
                        stream.close()
                        audio.terminate()

                        # Check if speech is long enough
                        speech_duration = (
                            len(self.audio_buffer) * self.CHUNK_SIZE / self.SAMPLE_RATE
                        )

                        if speech_duration >= self.MIN_SPEECH_DURATION:
                            self.gui.show_recognize_image()
                            print("🧠 Processing speech...")

                            # Transcribe
                            result = self._transcribe_buffer()
                            self.gui.hide_listen_image()
                            return result
                        else:
                            # Too short, ignore
                            self.gui.hide_listen_image()
                            return ""
                elif self.is_speaking:
                    # Transitional state - buffer audio but don't change state
                    self.audio_buffer.append(audio_chunk)

        except Exception as e:
            print(f"\n⚠️ Listening error: {e}")
            try:
                stream.stop_stream()
                stream.close()
                audio.terminate()
            except:
                pass
            self.gui.hide_listen_image()
            return ""

    def _transcribe_buffer(self):
        """Transcribe buffered audio with Faster-Whisper"""
        try:
            # Combine all chunks
            audio_array = np.concatenate(self.audio_buffer)
            
            # Calculate duration for display
            duration = len(audio_array) / self.SAMPLE_RATE

            # Convert to float32 normalized to [-1.0, 1.0]
            audio_float = audio_array.astype(np.float32) / 32768.0

            # Transcribe with Faster-Whisper
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=int(self.MIN_SILENCE_DURATION * 1000),
                    threshold=0.3,
                ),
            )

            # Combine all segments
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            # Show what was heard (the key user request!)
            if transcription:
                print(f"\n👤 You said: \"{transcription}\"")
            else:
                print("❓ Couldn't understand that")
            
            return transcription

        except Exception as e:
            print(f"⚠️ Transcription error: {e}")
            return ""

    def _fallback_listen(self):
        """Fallback to old speech_recognition method"""
        with sr.Microphone() as source:
            self.gui.show_listen_image()
            print(">>>", end="\r")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source, 0, 8)

        try:
            self.gui.show_recognize_image()
            print("<<<", end="\r")
            query = self.recognizer.recognize_google(audio, language="en-in")
        except Exception as e:
            print("<!>", end="\r")
            self.gui.hide_listen_image()
            return ""
        return query


"---------------EXTRA----------------"


def music(Utility):
    Utility.intrOmsC()
    Utility.rockMsc(0.5)


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    # utils = Utility(spk, recog)
    # utils.open_setting()
    # utils.get_window("Code.exe", "HelperPHNX.py")
    # spk.speak("oohoom..!")
    # spk.speak("What's up!")
    # recog.take_command()
    spk.speak("Yoi, I'm back , you can continue your business now.", 169)
    # music(recog)
    # print("oj")
    # opn = OpenAppHandler(recog)
    # utils.speak("hello, sir")
    # utils.desKtoP(2)
    # utils.open_brave()
    # spk.speak("hello there!, It's Phoenix-The Desktop Assistant.")
    # sleep(1)
    # # spk.speak(
    # #     "So, Normally Makbook provides Siri, Samsung Provides bixby, but windows doesn't provide any voice assistant like that.. "
    # # )
    # # sleep(1)
    # # spk.speak(
    # #     "there was one cortana before, but they discontinued that project, it didn't work."
    # # )
    # # sleep(1)
    # spk.speak(
    #     "i totally work on voice command. i do small tasks like open-close any applications,maximize-minimize tabs, switching apps and switching between desktops."
    # )
    # sleep(1)
    # spk.speak(
    #     "Also i can adjust device brightness and volume. and ofcourse as a desktop assistant i have to play desired songs for you, if you want to listen song and don't know the song name? no worries i can suggest you song just ask me."
    # )
    # sleep(1)
    # spk.speak(
    #     "just like google assistant i can also set alarms, reminders, timers etc."
    # )
    # sleep(1)
    # spk.speak(
    #     "basically google assistant is not supported by the windows, and moin was working on me so he added these functionality in me."
    # )

    # sleep(1)
    # spk.speak(
    #     "i keep track of battery status..like for some specific stages i keep remind you about the battery status and after one stage i will remind you to plug in the charger."
    # )
