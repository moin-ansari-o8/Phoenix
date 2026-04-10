# QUICK FIX: Adding Queue Server to Phoenix

## Problem
Listener and processor create separate queues. They need to connect to the SAME shared queue.

## Solution: 3-Program Architecture
1. **queue_server.py** - Hosts the shared queue
2. **continuous_listener.py** - Connects to server, sends audio
3. **voice_command_processor.py** - Connects to server, receives audio

---

## Files Already Created
✅ `queue_server.py` - Queue server (DONE)

## Files to Update

### 1. Update `helpers/QueueManagerPHNX.py`

Replace the entire file with this simplified version that connects to the server:

```python
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
    audio_data: np.ndarray
    sample_rate: int
    timestamp: float
    duration: float
    energy_level: float

# Queue client manager
class QueueClientManager(BaseManager):
    pass

# Register remote queue
QueueClientManager.register('get_audio_queue')

def connect_to_queue_server(host='127.0.0.1', port=50000, authkey=b'phoenix_audio_queue'):
    try:
        logger.info(f"Connecting to queue server at {host}:{port}...")
        manager = QueueClientManager(address=(host, port), authkey=authkey)
        manager.connect()
        queue_obj = manager.get_audio_queue()
        logger.info("Connected to queue server!")
        return queue_obj
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        raise

class QueueManager:
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.queue = connect_to_queue_server()
        self._chunks_sent = 0
        self._chunks_received = 0
        self._chunks_dropped = 0
        logger.info("QueueManager initialized (connected to server)")
    
    # ... keep all other methods (send_chunk, receive_chunk, etc.) UNCHANGED
```

**Keep these methods as-is**:
- `send_chunk()`
- `receive_chunk()`
- `is_empty()`
- `get_size()`
- `get_stats()`
- `clear()`
- `close()`

### 2. Update `launch_phoenix.py`

Add queue server to the launcher. Three key changes:

**A. Add to __init__:**
```python
self.queue_server_process = None  # ADD THIS LINE
self.listener_process = None
self.processor_process = None
# ... rest stays same
```

**B. Add to _check_files_exist():**
```python
self.queue_server_script = os.path.join(self.base_dir, "queue_server.py")  # ADD THIS

# Then in _check_files_exist():
if not os.path.exists(self.queue_server_script):
    logger.error(f"Queue server script not found: {self.queue_server_script}")
    return False
logger.info(f"[OK] Queue server: {self.queue_server_script}")
```

**C. Add start_queue_server() method BEFORE start_processor():**
```python
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
            self.queue_server_process = subprocess.Popen([self.python_exe, self.queue_server_script])
        
        logger.info(f"[OK] Queue server started (PID: {self.queue_server_process.pid})")
        time.sleep(2)  # Let server start
        
        if self.queue_server_process.poll() is not None:
            logger.error("Queue server exited!")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Failed to start queue server: {e}")
        return False
```

**D. Update start() method to start queue server FIRST:**
```python
def start(self):
    # ... banner and file checks ...
    
    # START QUEUE SERVER FIRST
    if not self.start_queue_server():
        logger.error("Failed to start queue server!")
        return False
    
    # Then start processor
    if not self.start_processor():
        logger.error("Failed to start processor!")
        self.shutdown()
        return False
    
    # Then start listener
    if not self.start_listener():
        logger.error("Failed to start listener!")
        self.shutdown()
        return False
    
    self.monitor_processes()
    return True
```

**E. Update shutdown() to stop queue server too:**
```python
def shutdown(self):
    # ... stop listener ...
    # ... stop processor ...
    
    # ADD THIS:
    if self.queue_server_process and self.queue_server_process.poll() is None:
        logger.info("Stopping queue server...")
        try:
            self.queue_server_process.terminate()
            self.queue_server_process.wait(timeout=5)
            logger.info("[OK] Queue server stopped")
        except:
            self.queue_server_process.kill()
```

---

## Testing

1. Stop current Phoenix (Ctrl+C)
2. Apply the changes above
3. Run: `python launch_phoenix.py`
4. Speak: "hello there phoenix"
5. Check logs:
   - Should see processor receiving chunks
   - Should see transcription output
   - Should hear Phoenix respond

---

## What This Fixes

**Before**: Listener → Queue A, Processor → Queue B (SEPARATE!)
**After**: Listener → Server Queue ← Processor (SHARED!)

The queue server acts as a "middleman" that both processes connect to, ensuring they use the SAME queue.
