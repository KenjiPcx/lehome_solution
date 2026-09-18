#!/usr/bin/env python3
"""Adapt the existing DAgger collector to tunneled Mac leaders and browser UI."""

from __future__ import annotations

import json
import logging
import os
import select
import socket
import struct
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
os.environ.setdefault("VK_ICD_FILENAMES", "/workspace/lehome/nvidia_icd.json")
os.environ.setdefault("HF_HOME", "/workspace/lehome/hf-cache")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("WANDB_MODE", "disabled")

SOLUTION = Path(os.environ.get("LEHOME_SOLUTION", "/workspace/lehome/solution"))
sys.path.insert(0, str(SOLUTION))
from scripts import dagger_collect as dagger  # noqa: E402

dagger.SIM_BOOT_TIMEOUT = 600
dagger._SIM_START_ATTEMPTS = 1
logger = logging.getLogger("xlerobot.teleop")
CURRENT_UI_STATE = "BOOTING"


class StateReportingUI(dagger.DaggerUI):
    def update(self, *args, **kwargs):
        global CURRENT_UI_STATE
        CURRENT_UI_STATE = self.state
        return super().update(*args, **kwargs)


class TCPReader:
    """Provide the upstream SO101 reader interface from tunneled JSON packets."""

    def __init__(self, _left_port: str, _right_port: str):
        self.sock = None
        self.file = None
        self.latest = None
        self.latest_received_at = 0.0
        self.running = False
        self.thread = None
        self.profile = None
        self.last_action = None
        self.last_log = 0.0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                self.sock = socket.create_connection(("127.0.0.1", 18765), timeout=1)
                self.sock.settimeout(None)
                self.file = self.sock.makefile("r", encoding="utf-8")
                logger.info("Leader tunnel connected")
                for line in self.file:
                    packet = json.loads(line)
                    if "left" in packet and "right" in packet:
                        profile = packet.get("control_profile", "mirrored")
                        if profile != self.profile:
                            self.profile = profile
                            self.last_action = None
                            logger.info("Control orientation changed to %s", profile)
                        if self.latest is None:
                            logger.info("First complete leader packet received")
                        self.latest = packet
                        self.latest_received_at = time.monotonic()
            except (ConnectionError, OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Leader tunnel unavailable; holding robot: %s", exc)
            finally:
                self.latest = None
                if self.file:
                    self.file.close()
                if self.sock:
                    self.sock.close()
                self.file = self.sock = None
            if self.running:
                time.sleep(1)

    def get_action(self):
        if self.latest is None or time.monotonic() - self.latest_received_at > 0.25:
            return None
        raw_action = dagger.convert_bimanual_to_action(self.latest)
        try:
            action = dagger.map_bimanual_control(raw_action, self.profile)
        except ValueError:
            logger.warning("Unknown control profile %r; using direct", self.profile)
            action = dagger.map_bimanual_control(raw_action, "direct")
        now = time.monotonic()
        if now - self.last_log >= 1:
            delta = 0.0 if self.last_action is None else float(
                np.max(np.abs(action - self.last_action))
            )
            logger.info("Leader action received: max_delta=%.4f", delta)
            self.last_action = action.copy()
            self.last_log = now
        return action

    @property
    def is_alive(self):
        return self.running

    def stop(self):
        self.running = False
        if self.file:
            self.file.close()
        if self.sock:
            self.sock.close()


class TunnelCV:
    """Replace OpenCV display/input with a framed JPEG tunnel."""

    def __init__(self):
        self.sock = None

    def _connect(self):
        if self.sock is not None:
            return True
        try:
            self.sock = socket.create_connection(("127.0.0.1", 18766), timeout=0.1)
            self.sock.settimeout(None)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            logger.info("UI tunnel connected")
            return True
        except OSError:
            self.sock = None
            return False

    def _disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def show(self, _name, frame):
        if not self._connect():
            return
        height, width = frame.shape[:2]
        scale = min(1.0, 960 / width, 540 / height)
        if scale < 1:
            frame = cv2.resize(
                frame,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if not ok:
            raise RuntimeError("failed to encode DAgger UI frame")
        metadata = json.dumps(
            {"ui_state": CURRENT_UI_STATE, "sent_at": time.time()},
            separators=(",", ":"),
        ).encode()
        payload = metadata + b"\n" + encoded.tobytes()
        try:
            self.sock.sendall(struct.pack("!I", len(payload)) + payload)
        except OSError:
            self._disconnect()

    def key(self, _wait_ms):
        if not self._connect():
            return -1
        try:
            readable, _, _ = select.select([self.sock], [], [], 0.01)
            if not readable:
                return -1
            data = b""
            while len(data) < 4:
                chunk = self.sock.recv(4 - len(data))
                if not chunk:
                    self._disconnect()
                    return -1
                data += chunk
            return struct.unpack("!i", data)[0]
        except (OSError, ValueError):
            self._disconnect()
            return -1

    def close(self):
        self._disconnect()


def main():
    tunnel = TunnelCV()
    dagger.SO101ReaderProcess = TCPReader
    dagger.DaggerUI = StateReportingUI
    dagger.cv2.namedWindow = lambda *_args, **_kwargs: None
    dagger.cv2.setWindowProperty = lambda *_args, **_kwargs: None
    dagger.cv2.imshow = tunnel.show
    dagger.cv2.waitKeyEx = tunnel.key
    dagger.cv2.destroyAllWindows = tunnel.close
    dagger.main()


if __name__ == "__main__":
    main()
