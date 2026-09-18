#!/usr/bin/env python3
"""Bridge two Mac SO101 leaders to the persistent cloud DAgger session."""

from __future__ import annotations

import argparse
import json
import queue
import socket
import struct
import subprocess
import threading
import time
from pathlib import Path

import cv2
import numpy as np

MOTOR_NAMES = (
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
)
WINDOW = "LeHome Simulation Teleoperation"
ORIENTATIONS = {
    ord("1"): ("direct", "DIRECT"),
    ord("2"): ("same_side_180", "SAME-SIDE 180°"),
    ord("3"): ("crossed_180", "CROSSED 180°"),
}


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.leaders_connected = False
        self.video_connected = False
        self.ssh_connected = False
        self.control_profile = "same_side_180"
        self.status = "Connecting to persistent RunPod session..."
        self.keys: queue.SimpleQueue[int] = queue.SimpleQueue()
        self.stop = threading.Event()

    def clear_keys(self):
        while True:
            try:
                self.keys.get_nowait()
            except queue.Empty:
                return


class LeaderReader:
    def __init__(self, left_port: str, right_port: str, calibration_dir: Path):
        from lerobot.motors import Motor, MotorCalibration, MotorNormMode
        from lerobot.motors.feetech import FeetechMotorsBus

        def make_bus(port: str, calibration_path: Path):
            raw = json.loads(calibration_path.read_text())
            calibration = {
                name: MotorCalibration(
                    id=int(item["id"]), drive_mode=int(item["drive_mode"]),
                    homing_offset=int(item["homing_offset"]),
                    range_min=int(item["range_min"]), range_max=int(item["range_max"]),
                ) for name, item in raw.items()
            }
            motors = {
                name: Motor(
                    index, "sts3215",
                    MotorNormMode.RANGE_0_100 if name == "gripper" else MotorNormMode.DEGREES,
                ) for index, name in enumerate(MOTOR_NAMES, 1)
            }
            bus = FeetechMotorsBus(port=port, motors=motors, calibration=calibration)
            bus.connect()
            bus.disable_torque()
            return bus

        self.left = make_bus(left_port, calibration_dir / "aurochs_xlerobot_leaders_left.json")
        self.right = make_bus(right_port, calibration_dir / "aurochs_xlerobot_leaders_right.json")

    def read(self) -> dict:
        return {
            "left": self.left.sync_read("Present_Position", num_retry=2),
            "right": self.right.sync_read("Present_Position", num_retry=2),
            "ts": time.time(),
        }

    def close(self):
        for bus in (self.left, self.right):
            try:
                bus.disable_torque()
            finally:
                bus.disconnect()


def listener(port: int) -> socket.socket:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)
    sock.settimeout(1)
    return sock


def serve_leaders(sock: socket.socket, leaders: LeaderReader, state: State):
    while not state.stop.is_set():
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with state.lock:
                state.leaders_connected = True
            try:
                conn.sendall(b'{"status":"ready"}\n')
                while not state.stop.is_set():
                    started = time.monotonic()
                    payload = leaders.read()
                    with state.lock:
                        payload["control_profile"] = state.control_profile
                    payload = json.dumps(payload, separators=(",", ":")) + "\n"
                    conn.sendall(payload.encode())
                    state.stop.wait(max(0.0, 1 / 30 - (time.monotonic() - started)))
            except (ConnectionError, OSError):
                pass
            finally:
                with state.lock:
                    state.leaders_connected = False


def recv_exact(conn: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("socket closed")
        data.extend(chunk)
    return bytes(data)


def serve_video(sock: socket.socket, state: State):
    while not state.stop.is_set():
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with state.lock:
                state.video_connected = True
                state.status = "Connected — Space starts/pauses, Esc detaches, F11 toggles fullscreen"
            try:
                while not state.stop.is_set():
                    size = struct.unpack("!I", recv_exact(conn, 4))[0]
                    encoded = recv_exact(conn, size)
                    frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        raise ValueError("remote sent an undecodable frame")
                    with state.lock:
                        state.frame = frame
                    try:
                        key = state.keys.get_nowait()
                    except queue.Empty:
                        key = -1
                    conn.sendall(struct.pack("!i", key))
            except (ConnectionError, OSError, ValueError):
                pass
            finally:
                state.clear_keys()
                with state.lock:
                    state.video_connected = False
                    state.frame = None
                    state.status = "Simulator disconnected — reconnecting without replaying commands..."


def supervise_ssh(args, state: State):
    command = [
        "ssh", "-i", str(args.ssh_key), "-p", str(args.ssh_port),
        "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-R", f"127.0.0.1:{args.action_port}:127.0.0.1:{args.action_port}",
        "-R", f"127.0.0.1:{args.video_port}:127.0.0.1:{args.video_port}",
        f"root@{args.ssh_host}", args.remote_command,
    ]
    while not state.stop.is_set():
        proc = subprocess.Popen(command)
        with state.lock:
            state.ssh_connected = True
        while proc.poll() is None and not state.stop.wait(0.5):
            pass
        if state.stop.is_set() and proc.poll() is None:
            proc.terminate()
        with state.lock:
            state.ssh_connected = False
            state.status = "SSH disconnected — reconnecting..."
        state.stop.wait(2)


def show_ui(state: State):
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    fullscreen = True
    fullscreen_applied = False
    while not state.stop.is_set():
        with state.lock:
            frame = None if state.frame is None else state.frame.copy()
            status = state.status
            ssh_ok = state.ssh_connected
            leaders_ok = state.leaders_connected
            video_ok = state.video_connected
            profile = state.control_profile
        if frame is None:
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(frame, status, (55, 350), cv2.FONT_HERSHEY_SIMPLEX,
                        0.75, (220, 220, 220), 2, cv2.LINE_AA)
        badges = f"SSH {'ON' if ssh_ok else 'OFF'}   LEADERS {'ON' if leaders_ok else 'WAIT'}   VIDEO {'ON' if video_ok else 'WAIT'}"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 86), (20, 20, 20), -1)
        cv2.putText(frame, badges, (14, 27), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (80, 220, 140) if video_ok else (180, 180, 180), 1, cv2.LINE_AA)
        mode_label = next(label for value, label in ORIENTATIONS.values() if value == profile)
        cv2.putText(frame, f"Orientation: {mode_label}   [1 Direct] [2 Same-side 180] [3 Crossed 180]",
                    (14, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 210, 90), 1, cv2.LINE_AA)
        # Compact top-down mapping: leaders above, simulated followers below.
        x0 = frame.shape[1] - 185
        for x, label in ((x0, "L"), (x0 + 120, "R")):
            cv2.circle(frame, (x, 18), 11, (130, 130, 130), 1)
            cv2.circle(frame, (x, 70), 11, (80, 220, 140), 1)
            cv2.putText(frame, label, (x - 5, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
        if profile == "crossed_180":
            pairs = (((x0, 30), (x0 + 120, 58)), ((x0 + 120, 30), (x0, 58)))
        else:
            pairs = (((x0, 30), (x0, 58)), ((x0 + 120, 30), (x0 + 120, 58)))
        for start, end in pairs:
            cv2.arrowedLine(frame, start, end, (240, 210, 90), 1, tipLength=0.25)
        cv2.imshow(WINDOW, frame)
        key = cv2.waitKeyEx(30)
        if not fullscreen_applied:
            cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            fullscreen_applied = True
        if key == 27 or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            state.stop.set()
        elif key in ORIENTATIONS:
            with state.lock:
                state.control_profile = ORIENTATIONS[key][0]
                state.status = f"Orientation changed to {ORIENTATIONS[key][1]} — re-anchored at current pose"
                state.clear_keys()
        elif key in (0x01000034, 0xFFC8):
            fullscreen = not fullscreen
            cv2.setWindowProperty(
                WINDOW, cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
            )
        elif key >= 0:
            state.keys.put(int(key & 0xFF))
    cv2.destroyAllWindows()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-port", required=True)
    parser.add_argument("--right-port", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--ssh-port", required=True, type=int)
    parser.add_argument("--ssh-key", required=True, type=Path)
    parser.add_argument("--remote-command", required=True)
    parser.add_argument("--calibration-dir", type=Path, default=Path.home() / ".cache/huggingface/lerobot/calibration/teleoperators/so_leader")
    parser.add_argument("--action-port", type=int, default=18765)
    parser.add_argument("--video-port", type=int, default=18766)
    args = parser.parse_args()

    state = State()
    leaders = LeaderReader(args.left_port, args.right_port, args.calibration_dir)
    action_sock, video_sock = listener(args.action_port), listener(args.video_port)
    threading.Thread(target=serve_leaders, args=(action_sock, leaders, state), daemon=True).start()
    threading.Thread(target=serve_video, args=(video_sock, state), daemon=True).start()
    threading.Thread(target=supervise_ssh, args=(args, state), daemon=True).start()
    try:
        show_ui(state)
    finally:
        state.stop.set()
        action_sock.close()
        video_sock.close()
        leaders.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
