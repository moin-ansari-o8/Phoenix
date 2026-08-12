"""
Background Voice Processor for Phoenix
Receives audio chunks from queue, transcribes, processes commands, and speaks responses
"""

import sys
import os
import time
import signal
import tkinter as tk
import logging
from datetime import datetime
from typing import Optional

import numpy as np

# Get root directory for logging
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add project root to path so absolute imports like `Utils.limbs...` resolve
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

# Setup logging (file only, console has clean output). Was basicConfig at DEBUG
# writing bg_voice_processor.log into the repo root - which is how that file
# reached 2.2 MB of comtypes COM refcount chatter with the real tracebacks
# buried in it. Set PHOENIX_LOG_LEVEL=DEBUG for a noisy run.
from core.logging_setup import setup_logging
from core.trace import emit as trace_emit

logger = setup_logging("processor")


# Import handlers and helpers
from core.config import AppConfig
from Utils.limbs.audio_capture import SAMPLE_RATE
from Utils.limbs.queue_manager import QueueManager, AudioChunk
from Utils.limbs.speech_filters import (
    HallucinationFilter,
    SelfEchoFilter,
    TranscriptionCandidate,
)
from Utils.limbs.wake_gate import WakeGate
from Utils.limbs.lexicon import get_lexicon
from Utils.limbs.speaker_id import get_verifier
from Utils.limbs.assistant_io import VoiceAssistantGUI, SpeechEngine
from Utils.limbs.action_utilities import Utility, OpenAppHandler, CloseAppHandler
from Utils.limbs.command_processor import PhoenixAssistant
from Utils.limbs.console_ui import (
    user_said,
    phoenix_said,
    listening,
    print_block,
    get_timestamp,
)
from Utils.limbs.time_handlers import (
    TimerHandle,
    AlarmHandle,
    ReminderHandle,
    ScheduleHandle,
)

# Faster-Whisper for offline speech recognition
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed. Processor will not work without it!")


class VoiceProcessor:
    """Background voice command processor"""

    # Wake words that trigger processing (same as original main_assistant.py)
    from core.config import AppConfig

    WAKE_WORDS = AppConfig.wake_words

    def __init__(self, queue_manager):
        """
        Initialize voice processor

        Args:
            queue_manager: QueueManager instance for receiving chunks
        """
        self.queue_manager = queue_manager
        self.running = False
        self.chunks_processed = 0
        self.errors_count = 0
        self.transcriptions_count = 0
        self.chunks_dropped = 0

        # Wake word / follow-up state. A deadline, not a flag - see wake_gate.py
        # for why the previous boolean could never turn itself off.
        self.wake_gate = WakeGate(
            wake_words=self.WAKE_WORDS,
            followup_window_seconds=float(
                AppConfig.audio.get("followup_window_seconds", 30)
            ),
        )

        logger.info("Initializing VoiceProcessor...")

        # Initialize GUI (hidden for background process)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide GUI window
        self.gui = VoiceAssistantGUI(self.root)

        # Initialize speech engine
        self.speech_engine = SpeechEngine.shared()

        # Initialize utilities (without VoiceRecognition - we handle transcription here)
        self.utility = Utility(spk=self.speech_engine, reco=None)

        # Initialize Faster-Whisper for transcription
        self.whisper_model = None

        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not available! Install with: pip install faster-whisper"
            )

        try:
            self._load_whisper()
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            raise RuntimeError("Whisper is required for voice processor!")

        # Transcript-level defences (see Utils/limbs/speech_filters)
        stt_cfg = AppConfig.stt
        self.hallucination_filter = HallucinationFilter(
            max_no_speech_prob=float(stt_cfg.get("max_no_speech_prob", 0.6)),
            min_avg_logprob=float(stt_cfg.get("min_avg_logprob", -1.0)),
            min_voiced_ms=float(AppConfig.audio.get("min_voiced_ms", 400)),
            wake_words=list(self.WAKE_WORDS),
        )
        self.echo_filter = SelfEchoFilter()
        # Vocabulary repair for romanised Hindi/Gujarati and known mishearings.
        # Built here rather than lazily so a broken data/lexicon.json shows up at
        # startup instead of on the first command.
        self.lexicon = get_lexicon()
        # Speaker filter. Starts in "log" mode: it scores every utterance and
        # suppresses nothing until a threshold has been chosen from real data.
        self.speaker = get_verifier()
        logger.info(
            "Speaker verification: enabled=%s mode=%s enrolled=%s threshold=%.2f",
            self.speaker.enabled,
            self.speaker.mode,
            self.speaker.enrolled,
            self.speaker.threshold,
        )

        logger.info("Initializing Phoenix handlers...")

        # Initialize handlers
        self.open_handler = OpenAppHandler(self.utility)
        self.close_handler = CloseAppHandler(self.utility)
        self.timer_handle = TimerHandle(self.utility)
        self.alarm_handle = AlarmHandle(self.utility)
        self.reminder_handle = ReminderHandle(self.utility)
        self.schedule_handle = ScheduleHandle(self.utility)

        # Initialize PhoenixAssistant (intent matcher and action executor)
        self.phoenix_assistant = PhoenixAssistant(
            utility=self.utility,
            open_handler=self.open_handler,
            close_handler=self.close_handler,
            timer_handle=self.timer_handle,
            alarm_handle=self.alarm_handle,
            schedule_handle=self.schedule_handle,
            reminder_handle=self.reminder_handle,
        )

        logger.info("VoiceProcessor initialized successfully")

    def _resolve_device(self, requested: str):
        """
        Pick the Whisper device.

        The old code asked `torch.cuda.is_available()`, but torch here is a
        CPU-only build while CTranslate2 -- the library that actually runs the
        model -- can see the GPU perfectly well. So the probe answered "no GPU"
        for the wrong reason and pinned STT to the CPU permanently.  We now ask
        CTranslate2 directly.

        The default stays CPU regardless: this box has 4 GB of VRAM and Ollama
        already occupies most of it, so borrowing VRAM for STT would slow the
        LLM down by more than it speeds up transcription.
        """
        if requested in ("cpu", "cuda"):
            device = requested
        else:
            device = "cpu"  # "auto" - see docstring

        if device == "cuda":
            try:
                import ctranslate2

                if ctranslate2.get_cuda_device_count() < 1:
                    logger.warning("CUDA requested but no device visible; using CPU")
                    device = "cpu"
            except Exception as exc:
                logger.warning(f"CUDA probe failed ({exc}); using CPU")
                device = "cpu"

        compute_type = "int8" if device == "cpu" else "int8_float16"
        return device, compute_type

    def _load_whisper(self):
        stt_cfg = AppConfig.stt
        model_name = stt_cfg.get("model", "base.en")
        device, compute_type = self._resolve_device(stt_cfg.get("device", "auto"))

        for attempt_device, attempt_compute in ((device, compute_type), ("cpu", "int8")):
            logger.info(
                f"Loading Faster-Whisper '{model_name}' on {attempt_device} "
                f"({attempt_compute})..."
            )
            kwargs = {"device": attempt_device, "compute_type": attempt_compute}
            if attempt_device == "cpu":
                # 6 physical cores here; more threads than that buys ~2%.
                kwargs["cpu_threads"] = 6

            try:
                model = WhisperModel(model_name, **kwargs)

                # Warm up on the real code path. A cold model costs a couple of
                # seconds on its first call, and this is also where a broken
                # CUDA install surfaces: the model loads fine and only fails at
                # encode time with a missing cublas DLL, so warming up on GPU is
                # the only way to find out before the user's first command does.
                warm_start = time.time()
                list(
                    model.transcribe(
                        np.zeros(SAMPLE_RATE, dtype=np.float32),
                        language="en",
                        beam_size=1,
                    )[0]
                )
                self.whisper_model = model
                self.stt_device = attempt_device
                logger.info(
                    f"Whisper ready on {attempt_device} "
                    f"(warm-up {time.time() - warm_start:.2f}s)"
                )
                return
            except Exception as exc:
                if attempt_device == "cpu":
                    raise
                logger.warning(f"Whisper on {attempt_device} unusable ({exc}); using CPU")

    def has_wake_word(self, text: str) -> bool:
        """Word-boundary wake-word test. Kept for callers outside this class."""
        return self.wake_gate.find_wake(text) is not None

    def _runtime_trace(self, tag: str, message: str):
        """
        Emit one structured trace the TUI can parse without guessing.

        Kept as a (tag, message) call so the ~14 call sites did not all have to
        change; the wire format underneath is now JSON behind a sentinel, so a
        stray print() elsewhere can no longer be mistaken for a trace. See
        core/trace.py.
        """
        trace_emit(tag.lower(), text=message)

    def _announce_state(self, was_awake: bool):
        """
        Emit a VOICE_STATE trace only when dormant/awake actually flipped.

        The payload is a bare lowercase token because that is the protocol the
        TUI parsers expect - they compare the whole remainder of the line
        against a fixed set, so anything more descriptive is silently dropped.
        Wording belongs on the display side, in main.py and manager.py.
        """
        now_awake = self.wake_gate.is_awake
        if now_awake == was_awake:
            return
        self._runtime_trace("VOICE_STATE", "awake" if now_awake else "dormant")

    # faster-whisper truncates the hotword prompt at `max_length // 2` tokens
    # (see WhisperModel.get_prompt), i.e. 223 for every Whisper checkpoint.
    # Staying under it is not optional: past the limit the tail is silently
    # dropped, so the words at the end of the list simply do not exist as far as
    # the decoder is concerned.
    HOTWORD_TOKEN_BUDGET = 210

    def _build_dynamic_prompt(self) -> str:
        """
        Build the hotword string that biases Whisper toward words we expect.

        Whisper is autoregressive, so tokens placed in its context before
        decoding starts raise the probability of those spellings coming out.
        That is what turns a mangled "sa hiba" into "sahiba" and stops "igris"
        being transcribed as "increase".

        Two things this must get right, both learned the hard way:

        * **Priority, not alphabetical order.** The previous version collected
          every word longer than four characters out of all 807 intent patterns,
          `sorted()` them and kept the first 80. Alphabetical truncation keeps
          whatever sorts first, which has nothing to do with what matters -- the
          list was mostly A-to-C filler while song titles never appeared at all.

        * **Budget in TOKENS, not words.** 80 words is not a limit Whisper
          knows about; 223 tokens is. Counting with the model's own tokenizer is
          the only way to know where the cut actually falls.

        AppConfig is imported at module level and must NOT be re-imported here:
        a function-local import makes the name local for the whole body and
        raises UnboundLocalError above it. That is the bug that broke
        PhoenixAssistant on 2026-08-12; tests/test_startup_smoke.py guards it.
        """
        try:
            lexicon = get_lexicon()

            # Highest value first: if the budget cuts the list, it must cut the
            # least important end.
            #
            #   wake words - nothing downstream can recover a missed wake word
            #   names      - proper nouns an English model has never seen
            #   songs      - the whole reason this exists
            #   hinglish   - useful, but the repair layer covers most of it
            #   commands   - LAST, and first to be cut. These are English words
            #                being fed to an English model, which is the one
            #                thing it is already good at. They are here only in
            #                case stt.model is ever switched to a multilingual
            #                checkpoint, where English can drift.
            #
            # MEASURED: romanised Hindi tokenises at ~3.9 tokens per word, not
            # the ~1.3 an English word costs, so the full list is 429 tokens
            # against a 223 hard cap. Roughly half of it gets cut, every time.
            # That is expected and is why the repair layer exists -- a title
            # that misses the budget still resolves after transcription. What
            # matters is that the cut falls on the least valuable end, which is
            # entirely down to this ordering.
            groups = [
                [w.capitalize() for w in self.WAKE_WORDS],
                [str(getattr(AppConfig, "user_name", "User")).capitalize()],
                [n.capitalize() for n in lexicon.words("names")],
                lexicon.ranked_songs(),
                lexicon.words("hinglish"),
                lexicon.words("commands"),
            ]

            ordered = []
            seen = set()
            for group in groups:
                for word in group:
                    key = word.lower()
                    if word and key not in seen:
                        seen.add(key)
                        ordered.append(word)

            prompt = self._fit_to_token_budget(ordered)
            logger.info(
                "STT hotwords: %d words, %d tokens -- %s",
                len(prompt.split(", ")),
                self._count_tokens(prompt),
                prompt[:160] + ("..." if len(prompt) > 160 else ""),
            )
            return prompt

        except Exception as e:
            logger.error(f"Error building hotword prompt: {e}", exc_info=True)
            return "Phoenix, Igris, Kaly, brightness, volume, screenshot"

    def _count_tokens(self, text: str) -> int:
        """Token count using Whisper's own tokenizer, with a safe fallback."""
        try:
            return len(self.whisper_model.hf_tokenizer.encode(text).ids)
        except Exception:
            # ~3 chars per token is conservative for word lists; erring low
            # would let the real prompt overflow and be silently truncated.
            return len(text) // 3

    def _fit_to_token_budget(self, words):
        """Longest prefix of `words` that fits inside HOTWORD_TOKEN_BUDGET."""
        candidate = ", ".join(words)
        if self._count_tokens(candidate) <= self.HOTWORD_TOKEN_BUDGET:
            return candidate

        low, high = 0, len(words)
        while low < high:
            mid = (low + high + 1) // 2
            if self._count_tokens(", ".join(words[:mid])) <= self.HOTWORD_TOKEN_BUDGET:
                low = mid
            else:
                high = mid - 1
        logger.info("Hotword list trimmed to %d of %d words by token budget", low, len(words))
        return ", ".join(words[:low])

    def transcribe_audio(
        self, chunk: AudioChunk, hotwords_override: Optional[str] = None
    ) -> TranscriptionCandidate:
        """
        Transcribe an utterance with Faster-Whisper.

        Returns a TranscriptionCandidate carrying the text plus the two
        confidence signals Whisper exposes, which the hallucination filter needs
        to tell "the user said thank you" from "the model invented thank you
        because it was fed silence".

        `vad_filter` is deliberately off: the listener already ran Silero over
        this audio frame by frame, and re-running it here would be pure
        duplicated work on the critical path.
        """
        try:
            audio_float = chunk.audio_data.astype(np.float32) / 32768.0

            if getattr(self, "_dynamic_prompt", None) is None:
                self._dynamic_prompt = self._build_dynamic_prompt()
            hotwords = hotwords_override or self._dynamic_prompt

            started = time.time()
            segments, info = self.whisper_model.transcribe(
                audio_float,
                # Pinned to English on purpose, even for Hindi/Gujarati words.
                # Left to auto-detect, one Gujarati song title flips the whole
                # utterance into Gujarati mode and the output comes back in
                # Devanagari, which matches nothing in songs.txt or the lexicon.
                # Pinned to "en", the same word is treated as a loanword and
                # comes out romanised -- which is how the library is written.
                language="en",
                beam_size=int(AppConfig.stt.get("beam_size", 1)),
                # `hotwords`, not `initial_prompt`: this is the channel built for
                # vocabulary biasing, and it survives condition_on_previous_text
                # being off. See faster_whisper.WhisperModel.get_prompt.
                hotwords=hotwords,
                condition_on_previous_text=False,  # stops hallucination loops
                vad_filter=False,
                word_timestamps=False,
            )

            texts = []
            no_speech_prob = 0.0
            avg_logprob = 0.0
            for segment in segments:
                texts.append(segment.text)
                no_speech_prob = max(no_speech_prob, getattr(segment, "no_speech_prob", 0.0))
                avg_logprob = min(avg_logprob, getattr(segment, "avg_logprob", 0.0))

            elapsed = time.time() - started
            text = " ".join(texts).strip()

            self._runtime_trace(
                "STT",
                f"utt={chunk.duration:.1f}s voiced={chunk.voiced_ms/1000:.1f}s "
                f"stt={elapsed:.2f}s rtf={elapsed / max(chunk.duration, 0.01):.2f}",
            )

            if text:
                self.transcriptions_count += 1
                logger.info(
                    "Transcribed in %.2fs: '%s' (no_speech=%.2f, logprob=%.2f)",
                    elapsed,
                    text,
                    no_speech_prob,
                    avg_logprob,
                )

            return TranscriptionCandidate(
                text=text,
                duration=chunk.duration,
                voiced_ms=chunk.voiced_ms,
                no_speech_prob=no_speech_prob,
                avg_logprob=avg_logprob,
            )

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}", exc_info=True)
            return TranscriptionCandidate(text="")

    def _rerank_song_request(self, chunk: AudioChunk, transcription: str) -> str:
        """
        Second transcription pass, biased toward the titles that could plausibly
        have been said. Returns the transcription to actually use.

        ## Why this exists

        The hotword channel is capped at 223 tokens, and a romanised song title
        costs ~8.7 of them, so the bias layer holds about twenty titles NO MATTER
        HOW LARGE the library grows. At 200 songs that is 10% coverage. Biasing
        the first pass therefore cannot be the answer on its own.

        What makes it tractable is that retrieval and ranking fail differently.
        Fuzzy-matching a mangled title against the WHOLE library has no size
        limit and near-perfect recall -- measured 99.6% for the right title
        being somewhere in the top 8, against 92.9% for it being first. So:

            pass 1  -> plain transcription, general hotwords
            retrieve -> top 8 candidates from the entire library (~1ms, no cap)
            pass 2  -> re-transcribe the SAME audio biased to just those 8

        Eight titles always fit the budget, so library size stops mattering.

        ## When it runs

        Only in the ambiguous band. A confident match skips it, and so does a
        request with nothing plausible in the library:

            score >= SONG_CONFIDENT  -> pass 1 was right, no second pass
            score <  SONG_FLOOR      -> a new song, no second pass
            otherwise                -> re-transcribe

        So the ordinary case -- a known song, clearly spoken -- costs nothing
        extra, and only genuinely unclear requests pay for the extra pass.
        """
        lexicon = self.lexicon
        if not lexicon.is_song_request(transcription):
            return transcription

        slot = lexicon.extract_song_slot(transcription)
        if not slot:
            return transcription  # "play some music" - no title to disambiguate

        best = lexicon.resolve_song(slot, min_score=0)
        best_score = best[1] if best else 0.0

        if best_score >= lexicon.SONG_CONFIDENT:
            return transcription
        if best_score < lexicon.SONG_FLOOR:
            return transcription

        candidates = lexicon.candidates(slot)
        if not candidates:
            return transcription

        titles = [title for title, _ in candidates]
        started = time.time()
        second = self.transcribe_audio(chunk, hotwords_override=", ".join(titles))
        if not second.text:
            return transcription

        second_text, _ = lexicon.repair_transcript(second.text)
        second_slot = lexicon.extract_song_slot(second_text)
        second_best = lexicon.resolve_song(second_slot, min_score=0) if second_slot else None
        second_score = second_best[1] if second_best else 0.0

        self._runtime_trace(
            "SONG_RERANK",
            f"'{slot}' {best_score:.0f} -> '{second_slot}' {second_score:.0f} "
            f"({time.time() - started:.2f}s, {len(titles)} candidates)",
        )

        # Keep pass 1 unless pass 2 genuinely did better. A second pass that
        # scores no higher has told us nothing, and adopting it anyway would
        # trade a known result for a differently-wrong one.
        if second_score > best_score:
            logger.info(
                "Song rerank: '%s' (%.0f) -> '%s' (%.0f)",
                slot, best_score, second_slot, second_score,
            )
            return second_text
        return transcription

    def process_audio_chunk(self, chunk: AudioChunk):
        """
        Process one complete utterance.

        Flow:
        0. Is this the owner speaking?  (log-only until calibrated)
        1. Transcribe
        2. Reject Whisper hallucinations (silence artefacts)
        3. Reject / trim Phoenix's own voice, then repair mangled vocabulary
        4. Wake word gives one command; a matched command opens follow-up mode
        """
        try:
            logger.debug(f"Processing utterance: {chunk.duration:.2f}s")
            chunk_timestamp = datetime.fromtimestamp(chunk.timestamp).strftime(
                "%H:%M:%S"
            )

            # Step 0: is this the owner? Runs BEFORE Whisper on purpose -- an
            # embedding costs ~16ms against ~800ms for transcription, so a
            # rejected voice never reaches the expensive part. Fails open on
            # every uncertainty; see speaker_id.py.
            verdict_speaker = self.speaker.verify(chunk.audio_data)
            if verdict_speaker.verifiable:
                self._runtime_trace(
                    "SPEAKER",
                    f"score={verdict_speaker.score:.2f} "
                    f"threshold={self.speaker.threshold:.2f} "
                    + (
                        "match"
                        if verdict_speaker.accepted
                        else ("REJECT" if self.speaker.mode == "gate" else "would reject")
                    ),
                )
            if self.speaker.should_reject(verdict_speaker):
                logger.info("Speaker rejected (score %.2f)", verdict_speaker.score)
                self.chunks_processed += 1
                listening()
                return

            candidate = self.transcribe_audio(chunk)

            # Step 2: is this something Whisper invented?
            reason = self.hallucination_filter.rejection_reason(candidate)
            if reason:
                logger.info(f"Discarded '{candidate.text}': {reason}")
                self._runtime_trace("DISCARDED", f"{candidate.text or '<empty>'} ({reason})")
                self.chunks_processed += 1
                return

            # Step 3: is this Phoenix hearing itself? The acoustic gate in the
            # listener is the first line of defence; this is the second, and it
            # also catches speech from other Phoenix processes (battery/time
            # announcements are spoken by the TUI process, not this one).
            self.echo_filter.set_history(self.queue_manager.recent_tts())
            verdict = self.echo_filter.check(candidate.text)
            if verdict.rejected:
                logger.info(f"Self-echo rejected '{candidate.text}': {verdict.reason}")
                self._runtime_trace("SELF_ECHO", candidate.text)
                self.chunks_processed += 1
                return

            transcription = verdict.text
            if verdict.action == "trim":
                logger.info(f"Self-echo trimmed: {verdict.reason} -> '{transcription}'")

            # Step 3b: repair words the English model spelled phonetically.
            # Runs BEFORE the wake gate on purpose -- "phonix open brave" has to
            # become "phoenix open brave" while there is still a gate left to
            # pass. Scoped to names and known mishearings; see lexicon.py for why
            # it deliberately does not touch ordinary English.
            transcription, repairs = self.lexicon.repair_transcript(transcription)
            if repairs:
                logger.info("Lexicon repairs: %s", repairs)
                self._runtime_trace(
                    "REPAIRED",
                    ", ".join(f"{heard} -> {fixed}" for heard, fixed in repairs),
                )

            # Step 3c: a song request whose title landed in the ambiguous band
            # gets a second, narrowly-biased transcription pass. No-op for
            # everything else.
            transcription = self._rerank_song_request(chunk, transcription)

            user_said(transcription, chunk_timestamp)

            # Step 4: is this addressed to Phoenix?
            was_awake = self.wake_gate.is_awake
            decision = self.wake_gate.evaluate(transcription)

            if decision.action == "ignore":
                # Dormant and not addressed. Heard, transcribed, deliberately
                # not answered - this is the normal resting state. The reason
                # is attached because "ignored" alone cannot be told apart from
                # a rejected transcript or an expired follow-up window, and
                # those need different fixes.
                self._runtime_trace(
                    "IGNORED_HEARD",
                    f"{transcription}  [dormant: no '{self.WAKE_WORDS[0]}' in sentence]",
                )

            elif decision.action == "acknowledge":
                # Wake word on its own, nothing to route. Wake up so the next
                # sentence lands without needing the word again.
                self._runtime_trace("HEARD", transcription)
                logger.info(f"Wake word only: '{transcription}'")
                self.wake_gate.refresh()
                self._announce_state(was_awake)

            else:
                self._runtime_trace("HEARD", transcription)
                logger.info(f"{decision.trigger}: '{decision.query}'")
                self._runtime_trace("PROCESSING", f"{decision.trigger} mode")

                result = self.phoenix_assistant.main(decision.query)
                matched = result is not False
                self._runtime_trace("INTENT", "matched" if matched else "no match")

                # Starting media beats everything else. Phoenix has just filled
                # the room with audio it does not control and cannot see the end
                # of, and the mic hears all of it - the echo gate only covers
                # Phoenix's own speech. Staying awake means every mangled lyric
                # becomes a follow-up command; a real session searched the web
                # for "waalakhua, ari waalakhua" and burned 21s transcribing a
                # chorus. Say the wake word again to talk over the music.
                if self.phoenix_assistant.started_media:
                    self.phoenix_assistant.started_media = False
                    self.wake_gate.sleep()
                    self._runtime_trace(
                        "GATE", "media started - dormant until the wake word"
                    )
                # An explicit wake word is unambiguous intent, so it always
                # earns the window even if routing found nothing. A follow-up
                # only earns it by succeeding, so a room full of conversation
                # cannot keep Phoenix awake indefinitely.
                elif decision.trigger == "wake" or matched:
                    self.wake_gate.refresh()
                else:
                    self.wake_gate.sleep()
                self._announce_state(was_awake)

                # How long follow-ups stay free. Printed every turn so an
                # "it stopped listening to me" report has a number attached
                # instead of a guess.
                self._runtime_trace(
                    "GATE", f"awake for {self.wake_gate.seconds_remaining:.0f}s more"
                )

            listening()  # Back to listening
            self.chunks_processed += 1

        except Exception as e:
            self.errors_count += 1
            self.wake_gate.sleep()
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            listening()

    def _is_stale(self, chunk) -> bool:
        """
        Skip audio that has been waiting too long to still be worth answering.

        This loop is single-threaded: one Whisper pass at a time. When the room
        is noisy - and most of all when Phoenix has just played a song through
        the speakers, which the mic hears - utterances arrive faster than they
        can be transcribed and the queue becomes a backlog.

        Observed in a real session: transcription times climbing to 21.0s,
        20.2s, 18.9s while the processor ground through lyrics. Your actual
        question sits behind all of it, so the reply arrives half a minute late
        and over the music, which reads as "sometimes it speaks, sometimes it
        doesn't".

        Answering a question from 30 seconds ago is worse than not answering
        it: the moment has passed and the reply lands on top of whatever is
        happening now. So old audio is dropped, newest-first, and the drop is
        traced rather than silent.
        """
        max_age = float(AppConfig.audio.get("max_chunk_age_seconds", 12))
        if max_age <= 0:
            return False

        age = time.time() - getattr(chunk, "timestamp", time.time())
        if age <= max_age:
            return False

        self.chunks_dropped += 1
        logger.info(
            "Dropped stale chunk: %.1fs old (%.1fs of audio), queue is behind",
            age,
            getattr(chunk, "duration", 0.0),
        )
        self._runtime_trace("STALE", f"dropped audio {age:.0f}s old - queue behind")
        return True

    def main_loop(self):
        """Main processing loop - receives and processes chunks"""
        logger.info("Starting main processing loop...")
        self.running = True

        consecutive_empty_count = 0
        max_consecutive_empty = 50
        was_awake = self.wake_gate.is_awake

        while self.running:
            try:
                # Receive chunk from queue (0.1s timeout)
                chunk = self.queue_manager.receive_chunk(timeout=0.1)

                if chunk is not None:
                    consecutive_empty_count = 0
                    if self._is_stale(chunk):
                        continue
                    self.process_audio_chunk(chunk)
                    was_awake = self.wake_gate.is_awake
                else:
                    # The awake window can expire with no utterance to notice
                    # it. Behaviour is already correct without this - the gate
                    # is checked on read - but the UI would otherwise keep
                    # claiming "awake" until someone next spoke.
                    if was_awake and not self.wake_gate.is_awake:
                        self._announce_state(was_awake=True)
                        was_awake = False

                    # No chunk available
                    consecutive_empty_count += 1

                    if consecutive_empty_count >= max_consecutive_empty:
                        if consecutive_empty_count == max_consecutive_empty:
                            logger.debug(
                                "Queue empty for 5+ seconds, waiting for audio..."
                            )
                        consecutive_empty_count = 0  # Reset to avoid spam

                # Brief sleep to prevent CPU spinning
                time.sleep(0.01)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                break
            except Exception as e:
                self.errors_count += 1
                logger.error(f"Error in main loop: {e}", exc_info=True)
                # Continue running despite errors
                time.sleep(0.1)

        logger.info("Main loop stopped")

    def get_stats(self):
        """Get processor statistics"""
        return {
            "chunks_processed": self.chunks_processed,
            "transcriptions_count": self.transcriptions_count,
            "errors_count": self.errors_count,
            "queue_stats": self.queue_manager.get_stats(),
        }

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down VoiceProcessor...")
        self.running = False

        # Print statistics
        stats = self.get_stats()
        logger.info("=== Processor Statistics ===")
        logger.info(f"  Chunks processed: {stats['chunks_processed']}")
        logger.info(f"  Successful transcriptions: {stats['transcriptions_count']}")
        logger.info(f"  Errors: {stats['errors_count']}")
        logger.info(f"  Queue stats: {stats['queue_stats']}")

        # Cleanup
        try:
            self.root.destroy()
        except:
            pass

        logger.info("Shutdown complete")


class ProcessManager:
    """Manages the background processor lifecycle"""

    def __init__(self):
        self.processor = None
        self.queue_manager = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if self.processor:
            self.processor.shutdown()
        sys.exit(0)

    def start(self):
        """Start the background processor"""
        try:
            logger.info("=" * 70)
            logger.info("PHOENIX BACKGROUND VOICE PROCESSOR")
            logger.info("=" * 70)
            logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("")

            # Initialize queue manager
            logger.info("Initializing queue manager...")
            self.queue_manager = QueueManager(max_size=10)

            # Initialize processor
            logger.info("Initializing voice processor...")
            self.processor = VoiceProcessor(self.queue_manager)

            # Start main loop
            logger.info("Starting processing loop...")
            logger.info("Ready to receive audio chunks from listener!")
            logger.info("")

            self.processor.main_loop()

        except Exception as e:
            logger.critical(
                f"CRITICAL ERROR: Processor failed to start: {e}", exc_info=True
            )
            # The logger is file-only, so without this the TUI sees nothing at
            # all: no processor means nothing drains the audio queue, every
            # later trace stops, and the last status ("Processing...") stays on
            # screen forever. A crash must not be able to masquerade as a hang.
            # One line, no traceback - the TUI drops multi-line noise.
            trace_emit("fatal", text=f"{type(e).__name__}: {e}")
            sys.exit(1)
        finally:
            if self.processor:
                self.processor.shutdown()


if __name__ == "__main__":
    try:
        manager = ProcessManager()
        manager.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
