"""
System Plugin - System Power Controls
======================================

Handles system-level operations like shutdown, restart, hibernate, sleep.
Extracted from UtilitiesPHNX.py system control methods.

Actions:
    - shutdown: Shut down the computer
    - restart: Restart the computer
    - hibernate: Hibernate the computer
    - sleep: Put computer to sleep
    - lock: Lock the computer
    - logout: Log out current user
    - restart_phoenix: Restart Phoenix assistant
    - close_all_python: Close all Python processes
"""

import os
import subprocess
import sys
import time
from typing import Optional

from ..base import BasePlugin


class SystemPlugin(BasePlugin):
    """Plugin for system power and control operations."""

    PLUGIN_NAME = "system"
    PLUGIN_DESCRIPTION = "System power and control operations"

    def _register_actions(self) -> None:
        """Register all system-related actions."""
        # Power controls
        self.register("shutdown", self.shutdown, "Shut down the computer")
        self.register("restart", self.restart, "Restart the computer")
        self.register("hibernate", self.hibernate, "Hibernate the computer")
        self.register("sleep", self.sleep, "Put computer to sleep")
        self.register("lock", self.lock, "Lock the computer")
        self.register("logout", self.logout, "Log out current user")

        # Phoenix controls
        self.register(
            "restart_phoenix", self.restart_phoenix, "Restart Phoenix assistant"
        )
        self.register("stop_phoenix", self.stop_phoenix, "Stop Phoenix assistant")

        # Process controls
        self.register(
            "close_all_python", self.close_all_python, "Close all Python processes"
        )
        self.register(
            "close_bg_python", self.close_bg_python, "Close background Python processes"
        )

        # Connectivity
        self.register("bluetooth_toggle", self.bluetooth_toggle, "Toggle Bluetooth")
        self.register("hotspot_toggle", self.hotspot_toggle, "Toggle mobile hotspot")
        self.register("wifi_toggle", self.wifi_toggle, "Toggle WiFi")
        self.register("airplane_mode", self.airplane_mode, "Toggle airplane mode")

    # ==================== Power Controls ====================

    def shutdown(self, delay: int = 0) -> bool:
        """
        Shut down the computer.

        Args:
            delay: Seconds to wait before shutdown (default 0)

        Returns:
            True if command was issued
        """
        self.speak("Shutting down the computer. Goodbye sir.")
        time.sleep(1)

        try:
            if delay > 0:
                os.system(f"shutdown /s /t {delay}")
            else:
                os.system("shutdown /s /t 0")
            return True
        except Exception as e:
            print(f"[ERROR] Shutdown failed: {e}")
            return False

    def restart(self, delay: int = 0) -> bool:
        """
        Restart the computer.

        Args:
            delay: Seconds to wait before restart (default 0)

        Returns:
            True if command was issued
        """
        self.speak("Restarting the computer. See you soon sir.")
        time.sleep(1)

        try:
            if delay > 0:
                os.system(f"shutdown /r /t {delay}")
            else:
                os.system("shutdown /r /t 0")
            return True
        except Exception as e:
            print(f"[ERROR] Restart failed: {e}")
            return False

    def hibernate(self) -> bool:
        """
        Put the computer into hibernation.

        Returns:
            True if command was issued
        """
        self.speak("Hibernating the computer.")
        time.sleep(1)

        try:
            os.system("shutdown /h")
            return True
        except Exception as e:
            print(f"[ERROR] Hibernate failed: {e}")
            return False

    def sleep(self) -> bool:
        """
        Put the computer to sleep.

        Returns:
            True if command was issued
        """
        self.speak("Putting computer to sleep.")
        time.sleep(1)

        try:
            # Use rundll32 for sleep (more reliable than shutdown /h)
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return True
        except Exception as e:
            print(f"[ERROR] Sleep failed: {e}")
            return False

    def lock(self) -> bool:
        """
        Lock the computer.

        Returns:
            True if command was issued
        """
        self.speak("Locking the computer.")

        try:
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return True
        except Exception as e:
            print(f"[ERROR] Lock failed: {e}")
            return False

    def logout(self) -> bool:
        """
        Log out the current user.

        Returns:
            True if command was issued
        """
        self.speak("Logging out.")
        time.sleep(1)

        try:
            os.system("shutdown /l")
            return True
        except Exception as e:
            print(f"[ERROR] Logout failed: {e}")
            return False

    # ==================== Phoenix Controls ====================

    def restart_phoenix(self) -> bool:
        """
        Restart the Phoenix assistant.

        Returns:
            True if restart initiated
        """
        self.speak("Restarting Phoenix.")

        try:
            # Get Phoenix root directory
            phoenix_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            launch_script = os.path.join(phoenix_root, "launch_phoenix.py")

            if os.path.exists(launch_script):
                # Start new instance
                subprocess.Popen(
                    [sys.executable, launch_script],
                    cwd=phoenix_root,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )

                # Exit current instance
                time.sleep(1)
                sys.exit(0)
            else:
                self.speak("Could not find Phoenix launcher")
                return False

        except Exception as e:
            print(f"[ERROR] Phoenix restart failed: {e}")
            return False

    def stop_phoenix(self) -> bool:
        """
        Stop the Phoenix assistant.

        Returns:
            True if stop initiated
        """
        self.speak("Goodbye sir. Phoenix shutting down.")
        time.sleep(1)
        sys.exit(0)

    # ==================== Process Controls ====================

    def close_all_python(self) -> bool:
        """
        Close all Python processes (except this one).

        Returns:
            True if command was issued
        """
        self.speak("Closing all Python processes.")

        try:
            current_pid = os.getpid()
            # Kill all python.exe and pythonw.exe except current process
            os.system(f'taskkill /F /IM python.exe /FI "PID ne {current_pid}" 2>nul')
            os.system(f'taskkill /F /IM pythonw.exe /FI "PID ne {current_pid}" 2>nul')
            return True
        except Exception as e:
            print(f"[ERROR] Close Python failed: {e}")
            return False

    def close_bg_python(self) -> bool:
        """
        Close background Python processes (pythonw.exe).

        Returns:
            True if command was issued
        """
        self.speak("Closing background Python processes.")

        try:
            os.system("taskkill /F /IM pythonw.exe 2>nul")
            return True
        except Exception as e:
            print(f"[ERROR] Close background Python failed: {e}")
            return False

    # ==================== Connectivity ====================

    def bluetooth_toggle(self) -> bool:
        """
        Toggle Bluetooth on/off.

        Returns:
            True if command was issued
        """
        self.speak("Toggling Bluetooth.")

        try:
            # Open Bluetooth settings
            os.startfile("ms-settings:bluetooth")
            return True
        except Exception as e:
            print(f"[ERROR] Bluetooth toggle failed: {e}")
            return False

    def hotspot_toggle(self) -> bool:
        """
        Toggle mobile hotspot on/off.

        Returns:
            True if command was issued
        """
        self.speak("Opening hotspot settings.")

        try:
            os.startfile("ms-settings:network-mobilehotspot")
            return True
        except Exception as e:
            print(f"[ERROR] Hotspot toggle failed: {e}")
            return False

    def wifi_toggle(self) -> bool:
        """
        Toggle WiFi on/off.

        Returns:
            True if command was issued
        """
        self.speak("Opening WiFi settings.")

        try:
            os.startfile("ms-settings:network-wifi")
            return True
        except Exception as e:
            print(f"[ERROR] WiFi toggle failed: {e}")
            return False

    def airplane_mode(self) -> bool:
        """
        Toggle airplane mode.

        Returns:
            True if command was issued
        """
        self.speak("Opening airplane mode settings.")

        try:
            os.startfile("ms-settings:network-airplanemode")
            return True
        except Exception as e:
            print(f"[ERROR] Airplane mode toggle failed: {e}")
            return False
