"""
Phoenix Queue Fix Script
Run this to update all files for 3-program queue server architecture
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============ NEW QueueManagerPHNX.py ============
QUEUE_MANAGER_CONTENT = '''"""
Queue Manager for Phoenix Voice Assistant
Connects to queue server for cross-process queue sharing
"""

import multiprocessing as mp
from multiprocessing.managers import BaseManager
import queue
import numpy as np
import time
import logging
from typing import Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("QueueManager")


@dataclass
class AudioChunk:
    """Audio chunk with metadata for processing"""
    audio_data: np.ndarray
    sample_rate: int
    timestamp: float
    duration: float
    energy_level: float


class QueueClientManager(BaseManager):
    pass


QueueClientManager.register('get_audio_queue')


def connect_to_queue_server(host='127.0.0.1', port=50000, authkey=b'phoenix_audio_queue', retries=5):
    """Connect to the queue server with retries"""
    for attempt in range(retries):
        try:
            logger.info(f"Connecting to queue server at {host}:{port} (attempt {attempt+1}/{retries})...")
            manager = QueueClientManager(address=(host, port), authkey=authkey)
            manager.connect()
            queue_obj = manager.get_audio_queue()
            logger.info("Connected to queue server successfully!")
            return queue_obj
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Connection failed, retrying in 1s... ({e})")
                time.sleep(1)
            else:
                logger.error(f"Failed to connect to queue server after {retries} attempts: {e}")
                raise


class QueueManager:
    """Manages audio chunk queue between listener and processor"""

    def __init__(self, max_size: int = 10):
        """Initialize queue manager by connecting to queue server"""
        self.max_size = max_size
        self.queue = connect_to_queue_server()
        self._chunks_sent = 0
        self._chunks_received = 0
        self._chunks_dropped = 0
        logger.info("QueueManager initialized (connected to server)")

    def send_chunk(self, audio_chunk: AudioChunk, timeout: float = 0.1) -> bool:
        """Send audio chunk to queue"""
        try:
            self.queue.put(audio_chunk, block=True, timeout=timeout)
            self._chunks_sent += 1
            logger.debug(f"Chunk sent (total: {self._chunks_sent})")
            return True
        except queue.Full:
            self._chunks_dropped += 1
            logger.warning(f"Queue full! Chunk dropped. (sent: {self._chunks_sent}, dropped: {self._chunks_dropped})")
            return False
        except Exception as e:
            logger.error(f"Error sending chunk: {e}")
            return False

    def receive_chunk(self, timeout: float = 0.1) -> Optional[AudioChunk]:
        """Receive audio chunk from queue"""
        try:
            chunk = self.queue.get(block=True, timeout=timeout)
            self._chunks_received += 1
            logger.debug(f"Chunk received (total: {self._chunks_received})")
            return chunk
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error receiving chunk: {e}")
            return None

    def is_empty(self) -> bool:
        return self.queue.empty()

    def get_size(self) -> int:
        return self.queue.qsize()

    def get_stats(self):
        return {
            'chunks_sent': self._chunks_sent,
            'chunks_received': self._chunks_received,
            'chunks_dropped': self._chunks_dropped,
            'current_size': self.get_size(),
            'max_size': self.max_size
        }

    def clear(self):
        cleared = 0
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                cleared += 1
        except:
            pass
        if cleared > 0:
            logger.info(f"Cleared {cleared} chunks from queue")

    def close(self):
        logger.info("Queue connection closed")


def create_audio_chunk(audio_data: np.ndarray, sample_rate: int = 16000, energy_level: float = 0.0) -> AudioChunk:
    """Helper function to create AudioChunk"""
    timestamp = time.time()
    duration = len(audio_data) / sample_rate
    return AudioChunk(
        audio_data=audio_data,
        sample_rate=sample_rate,
        timestamp=timestamp,
        duration=duration,
        energy_level=energy_level
    )


if __name__ == "__main__":
    print("Testing queue connection...")
    try:
        qm = QueueManager()
        print(f"Connected! Queue size: {qm.get_size()}")
    except Exception as e:
        print(f"Failed: {e}")
        print("Make sure queue_server.py is running first!")
'''

# ============ NEW launch_phoenix.py ============
LAUNCH_PHOENIX_CONTENT = '''"""
Phoenix Launcher - Start Queue Server, Listener and Processor
"""

import subprocess
import sys
import os
import time
import signal
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phoenix_launcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PhoenixLauncher')


class PhoenixLauncher:
    def __init__(self):
        self.queue_server_process = None
        self.listener_process = None
        self.processor_process = None
        self.running = False
        self.restart_on_crash = True
        self.max_restart_attempts = 3
        self.processor_restart_count = 0
        
        self.python_exe = sys.executable
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.queue_server_script = os.path.join(self.base_dir, "queue_server.py")
        self.listener_script = os.path.join(self.base_dir, "continuous_listener.py")
        self.processor_script = os.path.join(self.base_dir, "bgprogs", "voice_command_processor.py")
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)

    def _print_banner(self):
        banner = """
========================================
   PHOENIX VOICE ASSISTANT
   3-Program Architecture
========================================
"""
        print(banner)
        logger.info("Phoenix Launcher Starting...")

    def _check_files_exist(self):
        logger.info("Checking required files...")
        
        for name, path in [
            ("Queue server", self.queue_server_script),
            ("Listener", self.listener_script),
            ("Processor", self.processor_script)
        ]:
            if not os.path.exists(path):
                logger.error(f"{name} not found: {path}")
                return False
            logger.info(f"[OK] {name}: {path}")
        return True

    def start_queue_server(self):
        try:
            logger.info("Starting queue server...")
            
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                self.queue_server_process = subprocess.Popen(
                    [self.python_exe, self.queue_server_script],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.queue_server_process = subprocess.Popen(
                    [self.python_exe, self.queue_server_script]
                )
            
            logger.info(f"[OK] Queue server started (PID: {self.queue_server_process.pid})")
            time.sleep(2)
            
            if self.queue_server_process.poll() is not None:
                logger.error("Queue server exited immediately!")
                return False
            
            logger.info("[OK] Queue server running")
            return True
        except Exception as e:
            logger.error(f"Failed to start queue server: {e}")
            return False

    def start_processor(self):
        try:
            logger.info("Starting processor...")
            
            if sys.platform == 'win32':
                python_exe = self.python_exe.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = self.python_exe
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
                self.processor_process = subprocess.Popen(
                    [python_exe, self.processor_script],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.processor_process = subprocess.Popen(
                    [self.python_exe, self.processor_script]
                )
            
            logger.info(f"[OK] Processor started (PID: {self.processor_process.pid})")
            time.sleep(3)
            
            if self.processor_process.poll() is not None:
                logger.error("Processor exited immediately!")
                return False
            
            logger.info("[OK] Processor running")
            return True
        except Exception as e:
            logger.error(f"Failed to start processor: {e}")
            return False

    def start_listener(self):
        try:
            logger.info("Starting listener...")
            
            self.listener_process = subprocess.Popen(
                [self.python_exe, self.listener_script],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            logger.info(f"[OK] Listener started (PID: {self.listener_process.pid})")
            time.sleep(2)
            
            if self.listener_process.poll() is not None:
                logger.error("Listener exited immediately!")
                return False
            
            logger.info("[OK] Listener running")
            return True
        except Exception as e:
            logger.error(f"Failed to start listener: {e}")
            return False

    def monitor_processes(self):
        logger.info("")
        logger.info("=" * 50)
        logger.info("PHOENIX IS READY!")
        logger.info("=" * 50)
        logger.info("Speak naturally and pause 0.8s to process.")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 50)
        
        self.running = True
        
        try:
            while self.running:
                # Check listener
                if self.listener_process.poll() is not None:
                    logger.error("Listener exited!")
                    self.shutdown()
                    break
                
                # Check processor
                if self.processor_process.poll() is not None:
                    logger.warning("Processor exited!")
                    if self.restart_on_crash and self.processor_restart_count < self.max_restart_attempts:
                        self.processor_restart_count += 1
                        logger.info(f"Restarting processor ({self.processor_restart_count}/{self.max_restart_attempts})...")
                        if self.start_processor():
                            continue
                    self.shutdown()
                    break
                
                # Check queue server
                if self.queue_server_process.poll() is not None:
                    logger.error("Queue server exited!")
                    self.shutdown()
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        logger.info("Shutting down Phoenix...")
        self.running = False
        
        for name, proc in [
            ("Listener", self.listener_process),
            ("Processor", self.processor_process),
            ("Queue server", self.queue_server_process)
        ]:
            if proc and proc.poll() is None:
                logger.info(f"Stopping {name}...")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info(f"[OK] {name} stopped")
                except:
                    proc.kill()
        
        logger.info("Phoenix shutdown complete")

    def start(self):
        self._print_banner()
        
        if not self._check_files_exist():
            logger.error("Required files missing!")
            return False
        
        logger.info("")
        logger.info("Starting Phoenix components...")
        
        if not self.start_queue_server():
            return False
        
        if not self.start_processor():
            self.shutdown()
            return False
        
        if not self.start_listener():
            self.shutdown()
            return False
        
        self.monitor_processes()
        return True


if __name__ == "__main__":
    try:
        launcher = PhoenixLauncher()
        launcher.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)
'''


def apply_fixes():
    print("=" * 50)
    print("Phoenix Queue Fix Script")
    print("=" * 50)
    print()

    # Backup and update QueueManagerPHNX.py
    queue_manager_path = os.path.join(BASE_DIR, "helpers", "QueueManagerPHNX.py")
    queue_manager_backup = queue_manager_path + ".backup"

    print(f"1. Backing up {queue_manager_path}...")
    if os.path.exists(queue_manager_path):
        shutil.copy2(queue_manager_path, queue_manager_backup)
        print(f"   Backup: {queue_manager_backup}")

    print(f"   Updating QueueManagerPHNX.py...")
    with open(queue_manager_path, "w", encoding="utf-8") as f:
        f.write(QUEUE_MANAGER_CONTENT)
    print("   [OK] QueueManagerPHNX.py updated")
    print()

    # Backup and update launch_phoenix.py
    launch_path = os.path.join(BASE_DIR, "launch_phoenix.py")
    launch_backup = launch_path + ".backup"

    print(f"2. Backing up {launch_path}...")
    if os.path.exists(launch_path):
        shutil.copy2(launch_path, launch_backup)
        print(f"   Backup: {launch_backup}")

    print(f"   Updating launch_phoenix.py...")
    with open(launch_path, "w", encoding="utf-8") as f:
        f.write(LAUNCH_PHOENIX_CONTENT)
    print("   [OK] launch_phoenix.py updated")
    print()

    print("=" * 50)
    print("DONE! All fixes applied.")
    print("=" * 50)
    print()
    print("Now run: python launch_phoenix.py")
    print()


if __name__ == "__main__":
    apply_fixes()
