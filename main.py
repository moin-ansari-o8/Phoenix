"""
Phoenix unified main entry point.

Runs all 3 background programs in threads:
- Battery monitor
- Time monitor
- Voice processor
"""

from utils.background import (
    BatteryMonitorConfig,
    PhoenixRuntimeManager,
    RuntimeConfig,
    TimeMonitorConfig,
    VoiceProcessorConfig,
)


# Edit these runtime parameters from one place.
RUNTIME_CONFIG = RuntimeConfig(
    battery=BatteryMonitorConfig(
        initial_delay_seconds=5.0,
        check_interval_seconds=10.0,
        trigger_cooldown_seconds=600.0,
    ),
    time=TimeMonitorConfig(
        loop_interval_seconds=1.0,
        startup_water_delay_seconds=10.0,
        periodic_project_check_hours=6,
    ),
    voice=VoiceProcessorConfig(
        auto_restart=True,
        restart_delay_seconds=2.0,
    ),
)


def main():
    print("[main] Phoenix runtime manager starting...")
    manager = PhoenixRuntimeManager(config=RUNTIME_CONFIG)
    manager.run_forever()


if __name__ == "__main__":
    main()

