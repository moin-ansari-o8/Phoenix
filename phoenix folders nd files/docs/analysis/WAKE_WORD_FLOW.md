# Wake Word Flow - Investigation Results

## What I Understood From Your Request

You had a **2-step wake word system** like Google Assistant:

| Step | You Say | Has Wake Word? | Loop State | Result |
|------|---------|----------------|------------|--------|
| 1 | "Phoenix, open chrome" | YES | False | Process it, set loop=True |
| 2 | "set timer 5 minutes" | NO | True (follow-up) | Process anyway |
| 3 | (empty/no match) | - | - | Reset loop=False |
| 4 | "open notepad" | NO | False | IGNORED |
| 5 | "Phoenix, what time" | YES | False | Process it, set loop=True |

---

## How Original main_assistant.py Worked

### The `input_voice()` method (lines 437-475):

```python
def input_voice(self):
    self.loop = False
    while True:
        sent = self.takeCommand().lower().strip()
        
        # CASE 1: Has wake word AND loop is False
        if ("phoenix" in sent or "finish" in sent or ...) and self.loop == False:
            self.handle_command(sent)  # Process it
            # Inside handle_command: if match found → loop = True
        
        # CASE 2: Loop is True (follow-up mode)
        elif self.loop == True:
            self.handle_command(sent)  # Process WITHOUT wake word
        
        # CASE 3: Empty transcription
        elif not sent:
            self.loop = False  # Reset
        
        # CASE 4: No wake word, loop is False
        else:
            self.loop = False  # Ignore and reset
```

### Where `loop` gets set to True (line 609):

```python
def handle_command(self, sent):
    # ... intent matching ...
    if tag:  # Intent matched
        self._execute_action(tag, query_main)
        self.loop = True   # Enable follow-up mode
    else:
        self.loop = False  # No match, disable follow-up
```

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                   input_voice() LOOP                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Listen for speech                               │
│                                                     │
│  2. If wake word ("phoenix" etc) AND loop=False:    │
│     → Process command                               │
│     → If intent matched: loop = True                │
│     → If no match: loop = False                     │
│                                                     │
│  3. If loop=True (follow-up mode):                  │
│     → Process WITHOUT wake word                     │
│     → If intent matched: loop stays True            │
│     → If no match/empty: loop = False               │
│                                                     │
│  4. If no wake word AND loop=False:                 │
│     → IGNORE (don't process)                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Wake Words List (from main_assistant.py line 452-459)

- "phoenix"
- "finish" (sounds like phoenix)
- "feelings"
- "feeling"
- "friend"
- "buddy"
- "love"
- "baby"

---

## Current Problem

In the new 2-program architecture (`voice_command_processor.py`), I did NOT include this wake word logic. It processes ALL speech regardless of wake word.

---

## My Proposed Fix

Add this logic to `voice_command_processor.py`:

```python
class VoiceProcessor:
    def __init__(self):
        self.loop = False  # Follow-up mode flag
        self.WAKE_WORDS = [
            "phoenix", "finish", "feelings", "feeling", 
            "friend", "buddy", "love", "baby"
        ]
    
    def has_wake_word(self, text):
        """Check if text contains any wake word"""
        return any(word in text.lower() for word in self.WAKE_WORDS)
    
    def process_audio_chunk(self, chunk):
        transcription = self.transcribe_audio(chunk)
        
        if not transcription:
            self.loop = False  # Empty = reset
            return
        
        # Wake word logic
        if self.has_wake_word(transcription) and not self.loop:
            # Wake word detected, process it
            result = self.phoenix_assistant.main(transcription)
            self.loop = result  # True if matched, False if not
            
        elif self.loop:
            # Follow-up mode, no wake word needed
            result = self.phoenix_assistant.main(transcription)
            self.loop = result
            
        else:
            # No wake word, not in follow-up mode = IGNORE
            logger.debug(f"Ignored (no wake word): '{transcription}'")
            self.loop = False
```

---

## Question For You

Should I implement this wake word logic in the new system?

- **YES** → Restore original behavior (must say "phoenix" first)
- **NO** → Keep current behavior (responds to everything)

Let me know!
