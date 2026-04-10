"""
Phoenix Launcher - Start Queue Server, Listener and Processor
Launches the 3-program Phoenix voice assistant system
"""

import subprocess
import sys
import os
import time
import signal
import logging
from datetime import datetime

# Setup logging (file only - console has clean TUI output)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("phoenix_launcher.log")],
)
logger = logging.getLogger("PhoenixLauncher")


class PhoenixLauncher:
    """Manages Phoenix processes: Queue Server, Listener, and Processor"""

    def __init__(self):
        self.queue_server_process = None
        self.listener_process = None
        self.processor_process = None
        self.running = False
        self.restart_on_crash = True
        self.max_restart_attempts = 3
        self.processor_restart_count = 0

        # Get Python executable
        self.python_exe = sys.executable

        # Get script paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.queue_server_script = os.path.join(self.base_dir, "queue_server.py")
        self.listener_script = os.path.join(self.base_dir, "continuous_listener.py")
        self.processor_script = os.path.abspath(
            os.path.join(self.base_dir, "..", "utils", "background", "voice_command_processor.py")
        )

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down Phoenix...")
        self.shutdown()
        sys.exit(0)

    def _safe_print(self, text: str):
        """Print text safely even when terminal encoding cannot render unicode chars."""
        try:
            print(text)
        except UnicodeEncodeError:
            safe = text.encode("ascii", errors="replace").decode("ascii")
            print(safe)

    def _print_banner(self):
        """Print Phoenix banner"""
        banner = (
            "\n"
            "+-------------------------------------------------------------+\n"
            "|                    PHOENIX VOICE ASSISTANT                 |\n"
            "+-------------------------------------------------------------+\n"
            "| Speak naturally, pause 0.8s when done. Press Ctrl+C to exit.|\n"
            "+-------------------------------------------------------------+\n"
        )
        self._safe_print(banner)
        logger.info("Phoenix Launcher Starting...")
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _check_files_exist(self):
        """Verify required files exist"""
        logger.info("Checking required files...")

        if not os.path.exists(self.queue_server_script):
            logger.error(f"Queue server script not found: {self.queue_server_script}")
            self._safe_print("[ERROR] Queue server not found")
            return False

        if not os.path.exists(self.listener_script):
            logger.error(f"Listener script not found: {self.listener_script}")
            self._safe_print("[ERROR] Listener not found")
            return False

        if not os.path.exists(self.processor_script):
            logger.error(f"Processor script not found: {self.processor_script}")
            self._safe_print("[ERROR] Processor not found")
            return False

        return True

    def start_queue_server(self):
        """Start the queue server (required for IPC)"""
        try:
            logger.info("Starting queue server...")

            # Start queue server as hidden process on Windows
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

                self.queue_server_process = subprocess.Popen(
                    [self.python_exe, self.queue_server_script],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                self.queue_server_process = subprocess.Popen(
                    [self.python_exe, self.queue_server_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            logger.info(
                f"[OK] Queue server started (PID: {self.queue_server_process.pid})"
            )

            # Give queue server time to start
            time.sleep(1)

            # Check if still running
            if self.queue_server_process.poll() is not None:
                logger.error("Queue server exited immediately!")
                return False

            logger.info("[OK] Queue server ready")
            return True

        except Exception as e:
            logger.error(f"Failed to start queue server: {e}", exc_info=True)
            return False

    def start_processor(self):
        """Start the background processor"""
        try:
            logger.info("Starting background processor...")

            # Start processor with visible output (shares stdout with launcher)
            self.processor_process = subprocess.Popen(
                [self.python_exe, self.processor_script],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            logger.info(f"Processor started (PID: {self.processor_process.pid})")

            # Give processor time to initialize
            time.sleep(2)

            # Check if still running
            if self.processor_process.poll() is not None:
                logger.error("Processor exited immediately after start!")
                return False

            logger.info("Processor running")
            return True

        except Exception as e:
            logger.error(f"Failed to start processor: {e}", exc_info=True)
            return False

    def start_listener(self):
        """Start the listener"""
        try:
            logger.info("Starting listener...")

            # Start listener (visible window)
            self.listener_process = subprocess.Popen(
                [self.python_exe, self.listener_script],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            logger.info(f"[OK] Listener started (PID: {self.listener_process.pid})")

            # Give listener time to initialize
            time.sleep(2)

            # Check if still running
            if self.listener_process.poll() is not None:
                logger.error("Listener exited immediately after start!")
                return False

            logger.info("[OK] Listener running")
            return True

        except Exception as e:
            logger.error(f"Failed to start listener: {e}", exc_info=True)
            return False

    def monitor_processes(self):
        """Monitor all processes and restart if needed"""
        self._safe_print("[OK] Phoenix ready!\n")
        logger.info("Phoenix is ready")

        self.running = True

        try:
            while self.running:
                # Check queue server status
                if (
                    self.queue_server_process
                    and self.queue_server_process.poll() is not None
                ):
                    logger.error("Queue server died! Shutting down...")
                    self.shutdown()
                    break

                # Check listener status
                listener_status = self.listener_process.poll()
                if listener_status is not None:
                    logger.error(f"Listener exited with code {listener_status}")
                    logger.info("Shutting down (listener stopped)...")
                    self.shutdown()
                    break

                # Check processor status
                processor_status = self.processor_process.poll()
                if processor_status is not None:
                    logger.warning(f"Processor exited with code {processor_status}")

                    if (
                        self.restart_on_crash
                        and self.processor_restart_count < self.max_restart_attempts
                    ):
                        self.processor_restart_count += 1
                        logger.info(
                            f"Restarting processor (attempt {self.processor_restart_count}/{self.max_restart_attempts})..."
                        )

                        if self.start_processor():
                            logger.info("[OK] Processor restarted successfully")
                            continue
                        else:
                            logger.error("Failed to restart processor")
                            self.shutdown()
                            break
                    else:
                        logger.error(
                            "Processor crashed too many times or restart disabled"
                        )
                        self.shutdown()
                        break

                # Sleep before next check
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown all processes"""
        logger.info("Shutting down Phoenix...")
        self.running = False

        # Stop listener first
        if self.listener_process and self.listener_process.poll() is None:
            logger.info("Stopping listener...")
            try:
                self.listener_process.terminate()
                self.listener_process.wait(timeout=5)
                logger.info("[OK] Listener stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Listener didn't stop gracefully, forcing...")
                self.listener_process.kill()
            except Exception as e:
                logger.error(f"Error stopping listener: {e}")

        # Stop processor
        if self.processor_process and self.processor_process.poll() is None:
            logger.info("Stopping processor...")
            try:
                self.processor_process.terminate()
                self.processor_process.wait(timeout=5)
                logger.info("[OK] Processor stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Processor didn't stop gracefully, forcing...")
                self.processor_process.kill()
            except Exception as e:
                logger.error(f"Error stopping processor: {e}")

        # Stop queue server last
        if self.queue_server_process and self.queue_server_process.poll() is None:
            logger.info("Stopping queue server...")
            try:
                self.queue_server_process.terminate()
                self.queue_server_process.wait(timeout=3)
                logger.info("[OK] Queue server stopped")
            except subprocess.TimeoutExpired:
                self.queue_server_process.kill()
            except Exception as e:
                logger.error(f"Error stopping queue server: {e}")

        logger.info("Phoenix shutdown complete")

    def start(self):
        """Start Phoenix (queue server, processor, listener)"""
        self._print_banner()

        # Check files
        if not self._check_files_exist():
            logger.error("Required files missing! Cannot start Phoenix.")
            return False

        logger.info("")
        logger.info("Starting Phoenix components...")
        logger.info("")

        # Start queue server FIRST (required for IPC)
        if not self.start_queue_server():
            logger.error("Failed to start queue server! Aborting.")
            return False

        # Start processor second (background)
        if not self.start_processor():
            logger.error("Failed to start processor! Aborting.")
            self.shutdown()
            return False

        # Start listener last (foreground)
        if not self.start_listener():
            logger.error("Failed to start listener! Stopping all...")
            self.shutdown()
            return False

        # Monitor all processes
        self.monitor_processes()

        return True


def main():
    """Main entry point"""
    try:
        launcher = PhoenixLauncher()
        success = launcher.start()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
