"""
Is Phoenix allowed on the internet, and is there even an internet to be on?

`offline_mode` in core/config.json:

    true    always offline. Never probes, never dials out.
    false   always allowed (subject to web.enabled).
    "auto"  probe and decide. THE DEFAULT.

Why auto-detect rather than just a manual switch: the failure that actually
bites is not forgetting to flip a flag, it is Phoenix stalling on a dead
network. `web.fetch_timeout_seconds` is 8, and gather_context() may try
DuckDuckGo and then Wikipedia, so one question on a disconnected laptop could
block for ~20 s before answering. Auto-detection turns that into an instant,
honest "I can't look that up offline".

The probe is a **1-second TCP connect to a DNS server**, not an HTTP GET:

  - no DNS resolution, so a broken resolver does not read as "online"
  - no TLS handshake, no payload, no third-party service being pinged per query
  - fails immediately on a dead interface rather than waiting for a timeout

Results are cached briefly so a single turn never probes twice, and the cache is
short enough that pulling the wifi takes effect on the next command rather than
the next restart.
"""

from __future__ import annotations

import logging
import socket
import threading
import time

# Well-known anycast DNS resolvers, port 53. Two of them so one provider being
# unreachable is not mistaken for the whole internet being down.
PROBE_TARGETS = (("1.1.1.1", 53), ("8.8.8.8", 53))
PROBE_TIMEOUT_S = 1.0

# Long enough that a single turn probes at most once, short enough that
# unplugging the network is noticed almost immediately.
CACHE_TTL_ONLINE_S = 30.0
# Re-probe sooner when offline: coming back online should be picked up fast,
# and the probe is cheap precisely when it fails (no route = instant refusal).
CACHE_TTL_OFFLINE_S = 5.0


class ConnectivityMonitor:
    """Cached reachability probe. Thread-safe; several processes each hold one."""

    def __init__(self, targets=PROBE_TARGETS, timeout=PROBE_TIMEOUT_S):
        self.targets = tuple(targets)
        self.timeout = float(timeout)
        self._lock = threading.Lock()
        self._online = None       # None = never probed
        self._checked_at = 0.0
        self.probe_count = 0

    def _probe(self) -> bool:
        for host, port in self.targets:
            try:
                with socket.create_connection((host, port), timeout=self.timeout):
                    return True
            except OSError:
                continue
        return False

    def is_online(self, force: bool = False) -> bool:
        with self._lock:
            now = time.time()
            ttl = CACHE_TTL_ONLINE_S if self._online else CACHE_TTL_OFFLINE_S
            fresh = self._online is not None and (now - self._checked_at) < ttl
            if fresh and not force:
                return self._online

            was = self._online
            self.probe_count += 1
            self._online = self._probe()
            self._checked_at = now

            if was is not None and was != self._online:
                logging.info(
                    "[connectivity] network went %s",
                    "up" if self._online else "down",
                )
            return self._online

    def invalidate(self):
        """Drop the cache so the next question re-probes."""
        with self._lock:
            self._online = None
            self._checked_at = 0.0


_monitor = ConnectivityMonitor()


def get_monitor() -> ConnectivityMonitor:
    return _monitor


def _normalise(value) -> str:
    """config value -> one of 'on', 'off', 'auto'."""
    if isinstance(value, bool):
        return "off" if value else "on"
    text = str(value or "auto").strip().lower()
    if text in ("true", "yes", "1", "on"):
        return "off"        # offline_mode: true  => network OFF
    if text in ("false", "no", "0"):
        return "on"
    return "auto"


def network_allowed(reason: bool = False):
    """
    Whether a network call may be attempted right now.

    Combines three things, cheapest first:
      1. `web.enabled`   - the blunt user switch (see tool_registry.web_allowed)
      2. `offline_mode`  - the offline promise
      3. an actual reachability probe, when offline_mode is "auto"

    With `reason=True` returns `(allowed, why)` for logging and for telling the
    user *which* of the three stopped it - "you turned it off" and "there is no
    wifi" deserve different replies.
    """
    from core.config import AppConfig

    if not bool(AppConfig.web.get("enabled", True)):
        return (False, "web.enabled is false") if reason else False

    mode = _normalise(getattr(AppConfig, "offline_mode", "auto"))
    if mode == "off":
        return (False, "offline_mode is on") if reason else False
    if mode == "on":
        return (True, "network forced on") if reason else True

    online = _monitor.is_online()
    if online:
        return (True, "network reachable") if reason else True
    return (False, "no network detected") if reason else False


def refuses_because_offline() -> bool:
    """True when the block is a dead network rather than a user setting."""
    allowed, why = network_allowed(reason=True)
    return not allowed and why == "no network detected"
