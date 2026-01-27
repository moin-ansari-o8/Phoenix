"""
Advanced Speech-to-Text Listening System with Faster-Whisper
- Continuous listening with VAD-based smart chunking
- Real-time streaming transcription
- Processes chunks in background while continuing to listen
- Handles long speeches efficiently by chunking intelligently

Requirements:
    pip install faster-whisper sounddevice numpy torch torchaudio

Author: Phoenix Desktop Assistant
Date: January 2026
"""

import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import threading
import queue
import time
import sys
from collections import deque
import torch

# ============================================================================
# CONFIGURATION
# ============================================================================

# Audio Settings
SAMPLE_RATE = 16000  # Faster-Whisper requires 16kHz
CHANNELS = 1  # Mono audio
CHUNK_DURATION = 0.5  # Process audio in 0.5-second chunks
DTYPE = np.int16
AUDIO_DEVICE = None  # None = default, or specify device number

# VAD (Voice Activity Detection) Settings
VAD_THRESHOLD = 0.15  # Speech confidence threshold (0.0-1.0) - LOWERED for weak signals
MIN_SPEECH_DURATION = 0.3  # Minimum speech duration in seconds
MIN_SILENCE_DURATION = 0.8  # Silence duration to trigger processing (seconds)
SPEECH_PAD = 0.3  # Padding around speech segments (seconds)

# Energy-based detection (fallback for very weak signals)
ENERGY_THRESHOLD = 50  # RMS energy threshold (lowered for weak mics)
USE_ENERGY_DETECTION = True  # Enable energy-based detection alongside VAD

# Transcription Settings
WHISPER_MODEL = "small"  # Options: tiny, base, small, medium, large-v3
DEVICE = "cpu"  # "cpu" or "cuda" (GPU)
COMPUTE_TYPE = "int8"  # "int8" for CPU, "float16" for GPU
LANGUAGE = "en"  # Language code or None for auto-detect
BEAM_SIZE = 5  # Higher = more accurate but slower (1-10)

# Processing Settings
MAX_BUFFER_DURATION = 30  # Maximum audio buffer duration (seconds)
PROCESSING_OVERLAP = 1.0  # Overlap between chunks to avoid cutting words (seconds)

# ============================================================================
# COLORS FOR TERMINAL OUTPUT
# ============================================================================

class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ============================================================================
# SILERO VAD (Voice Activity Detection)
# ============================================================================

class SileroVAD:
    """Voice Activity Detection using Silero VAD model"""
    
    def __init__(self):
        try:
            # Load Silero VAD model (silently)
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            (self.get_speech_timestamps, _, _, _, _) = utils
        except Exception as e:
            self.model = None
    
    def detect_speech(self, audio_chunk, sample_rate=16000):
        """
        Detect if audio chunk contains speech
        
        Args:
            audio_chunk: numpy array (int16)
            sample_rate: audio sample rate
            
        Returns:
            bool: True if speech detected, False otherwise
        """
        if self.model is None:
            # Fallback: simple energy-based detection
            return self._energy_based_detection(audio_chunk)
        
        try:
            # Convert int16 to float32 normalized to [-1, 1]
            audio_float = audio_chunk.astype(np.float32) / 32768.0
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_float)
            
            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                sampling_rate=sample_rate,
                threshold=VAD_THRESHOLD,
                min_speech_duration_ms=int(MIN_SPEECH_DURATION * 1000),
                min_silence_duration_ms=int(MIN_SILENCE_DURATION * 1000),
                speech_pad_ms=int(SPEECH_PAD * 1000)
            )
            
            # If any speech detected, return True
            return len(speech_timestamps) > 0
            
        except Exception as e:
            print(f"{Colors.RED}[VAD] Error: {e}{Colors.RESET}")
            return self._energy_based_detection(audio_chunk)
    
    def _energy_based_detection(self, audio_chunk):
        """Fallback: simple energy-based speech detection"""
        if len(audio_chunk) == 0:
            return False
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
        
        # Use global threshold
        return rms > ENERGY_THRESHOLD


# ============================================================================
# STREAMING TRANSCRIBER
# ============================================================================

class StreamingTranscriber:
    """Main class for continuous speech-to-text with streaming"""
    
    def __init__(self):
        print(f"\n{Colors.CYAN}Phoenix Listening System - Initializing...{Colors.RESET}")
        
        # Initialize components
        self.vad = SileroVAD()
        self.model = None
        
        # Audio buffers
        self.audio_buffer = deque(maxlen=int(MAX_BUFFER_DURATION * SAMPLE_RATE))
        self.speech_buffer = []
        
        # Threading
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.processing_queue = queue.Queue()
        
        # State management
        self.is_running = False
        self.is_speaking = False
        self.speech_start_time = None
        self.silence_start_time = None
        self.last_speech_time = time.time()
        
        # Statistics
        self.total_transcriptions = 0
        self.total_words = 0
        
        # Load Whisper model
        self._load_model()
    
    def _load_model(self):
        """Load Faster-Whisper model"""
        try:
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=DEVICE,
                compute_type=COMPUTE_TYPE
            )
            print(f"{Colors.GREEN}Ready! Listening...{Colors.RESET}\n")
        except Exception as e:
            print(f"{Colors.RED}Error loading model: {e}{Colors.RESET}")
            sys.exit(1)
    
    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"{Colors.RED}[Audio] {status}{Colors.RESET}")
        
        # Convert to int16 and flatten
        audio_chunk = indata.flatten().astype(np.int16)
        
        # Add to queue for processing
        self.audio_queue.put(audio_chunk.copy())
    
    def _process_audio_thread(self):
        """Thread: Process incoming audio and detect speech"""
        while self.is_running:
            try:
                # Get audio chunk from queue (timeout to allow checking is_running)
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                # Add to buffer
                self.audio_buffer.extend(audio_chunk)
                
                # Detect speech using VAD and/or energy
                has_speech_vad = self.vad.detect_speech(audio_chunk, SAMPLE_RATE)
                
                # Also check energy level
                if USE_ENERGY_DETECTION:
                    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
                    has_speech_energy = rms > ENERGY_THRESHOLD
                    has_speech = has_speech_vad or has_speech_energy
                    
                    # Show audio level indicator
                
                current_time = time.time()
                
                if has_speech:
                    # Speech detected
                    if not self.is_speaking:
                        # Speech just started
                        self.is_speaking = True
                        self.speech_start_time = current_time
                        self.speech_buffer = []
                        print(f"\n{Colors.GREEN}🎤 [Speech Detected] Listening...{Colors.RESET}")
                    
                    # Add to speech buffer
                    self.speech_buffer.extend(audio_chunk)
                    self.last_speech_time = current_time
                    self.silence_start_time = None
                    
                    speech_duration = len(self.speech_buffer) / SAMPLE_RATE
                    if speech_duration >= (MAX_BUFFER_DURATION - PROCESSING_OVERLAP):
                        # Process this chunk and keep overlap
                        self._queue_for_transcription("chunk")
                
                else:
                    # No speech detected
                    if self.is_speaking:
                        # We were speaking, now silence
                        if self.silence_start_time is None:
                            self.silence_start_time = current_time
                        
                        # Add to speech buffer (to capture end of sentence)
                        self.speech_buffer.extend(audio_chunk)
                        
                        # Check if silence duration exceeded threshold
                        silence_duration = current_time - self.silence_start_time
                        if silence_duration >= MIN_SILENCE_DURATION:
                            # Silence long enough, process the speech
                            self._queue_for_transcription("complete")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"{Colors.RED}[Error] Audio processing: {e}{Colors.RESET}")
    
    def _queue_for_transcription(self, chunk_type="complete"):
        """Queue speech buffer for transcription"""
        if len(self.speech_buffer) == 0:
            return
        
        # Get speech duration
        speech_duration = len(self.speech_buffer) / SAMPLE_RATE
        
        # Only process if speech is long enough
        if speech_duration < MIN_SPEECH_DURATION:
            self.speech_buffer = []
            self.is_speaking = False
            return
        
        # Copy buffer for processing
        audio_to_process = np.array(self.speech_buffer, dtype=np.int16)
        
        # Add to processing queue
        self.processing_queue.put({
            'audio': audio_to_process,
            'duration': speech_duration,
            'type': chunk_type
        })
        
        if chunk_type == "complete":
            # Clear buffer and reset state
            self.speech_buffer = []
            self.is_speaking = False
        else:
            # Keep overlap for continuity
            overlap_samples = int(PROCESSING_OVERLAP * SAMPLE_RATE)
            self.speech_buffer = self.speech_buffer[-overlap_samples:]
    
    def _transcription_thread(self):
        """Thread: Transcribe queued audio"""
        while self.is_running:
            try:
                audio_data = self.processing_queue.get(timeout=0.1)
                
                audio_array = audio_data['audio']
                duration = audio_data['duration']
                chunk_type = audio_data['type']
                
                # Convert to float32 normalized to [-1, 1]
                audio_float = audio_array.astype(np.float32) / 32768.0
                
                # Transcribe
                start_time = time.time()
                
                segments, info = self.model.transcribe(
                    audio_float,
                    language=LANGUAGE,
                    beam_size=BEAM_SIZE,
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=int(MIN_SILENCE_DURATION * 1000),
                        threshold=VAD_THRESHOLD
                    )
                )
                
                # Collect all segments
                transcription = " ".join([segment.text.strip() for segment in segments])
                
                elapsed = time.time() - start_time
                
                # Put result in queue
                if transcription.strip():
                    self.result_queue.put({
                        'text': transcription.strip(),
                        'duration': duration,
                        'processing_time': elapsed,
                        'type': chunk_type,
                        'language': info.language,
                        'language_prob': info.language_probability
                    })
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"{Colors.RED}[Error] Transcription: {e}{Colors.RESET}")
    
    def _display_results_thread(self):
        """Thread: Display transcription results"""
        while self.is_running:
            try:
                # Get result from queue
                result = self.result_queue.get(timeout=0.1)
                
                text = result['text']
                duration = result['duration']
                proc_time = result['processing_time']
                
                # Update statistics
                self.total_transcriptions += 1
                word_count = len(text.split())
                self.total_words += word_count
                
                # Display result in requested format: [20 sec] [12 words] transcription text [3 sec]
                print(f"[{duration:.0f} sec] [{word_count} words] {text} [{proc_time:.0f} sec]")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"{Colors.RED}Display error: {e}{Colors.RESET}")
    
    def start(self):
        """Start the listening system"""
        self.is_running = True
        
        # Start worker threads
        audio_processor = threading.Thread(target=self._process_audio_thread, daemon=True)
        transcriber = threading.Thread(target=self._transcription_thread, daemon=True)
        displayer = threading.Thread(target=self._display_results_thread, daemon=True)
        
        audio_processor.start()
        transcriber.start()
        displayer.start()
        
        # Start audio stream
        try:
            with sd.InputStream(
                callback=self._audio_callback,
                channels=1,
                samplerate=SAMPLE_RATE,
                blocksize=int(CHUNK_DURATION * SAMPLE_RATE),
                dtype=np.int16
            ):
                # Keep running until interrupted
                while self.is_running:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Stopped.{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the listening system"""
        self.is_running = False
        time.sleep(0.5)
        
        # Display statistics
        if self.total_transcriptions > 0:
            print(f"\n{Colors.GREEN}Session: {self.total_transcriptions} transcriptions, {self.total_words} words{Colors.RESET}\n")


# ============================================================================
# Main
# ============================================================================

def main():
    """Main function"""
    try:
        transcriber = StreamingTranscriber()
        transcriber.start()
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()