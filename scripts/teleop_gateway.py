#!/usr/bin/env python3
"""Bridge two Mac SO101 leaders to a persistent cloud DAgger session."""

from __future__ import annotations

import argparse
import json
import queue
import socket
import struct
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lehome_solution.shared.real_robot_config import get_control_profile

MOTOR_NAMES = (
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
)
PROFILES = {
    "direct": "Direct",
    "mirrored": "Mirrored · invert base rotation",
}
COMMANDS = {"start_pause": ord(" "), "save": ord("s"), "retry": ord("r")}

HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>XLeRobot Teleoperation</title><style>
*{box-sizing:border-box}body{margin:0;background:#0d0e10;color:#eee;font:14px system-ui;height:100vh;display:grid;grid-template-rows:58px 1fr}
header{display:flex;align-items:center;gap:18px;padding:9px 16px;background:#17181b;border-bottom:1px solid #2d3036}
.brand{font-weight:650}.grow{flex:1}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#666;margin-right:5px}.on{background:#3ddc84}
select,button{background:#22252a;color:#eee;border:1px solid #454a53;border-radius:7px;padding:9px 12px}button{cursor:pointer;font-weight:650}.primary{background:#5a45ff;border-color:#7565ff;min-width:128px}.primary:disabled{cursor:wait;opacity:.72}.spin{display:inline-block;width:12px;height:12px;border:2px solid #aaa;border-top-color:#fff;border-radius:50%;animation:s .7s linear infinite;margin-right:7px;vertical-align:-2px}@keyframes s{to{transform:rotate(360deg)}}
main{min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:10px;padding:10px}.viewer{min-height:0;background:#050505;border:1px solid #292c31;border-radius:8px;display:flex;align-items:center;justify-content:center;overflow:hidden}.viewer img{width:100%;height:100%;object-fit:contain}
aside{background:#17181b;border:1px solid #292c31;border-radius:8px;padding:16px}.label{color:#888;text-transform:uppercase;font-size:11px;letter-spacing:.08em;margin-bottom:8px}.mapping{height:190px;background:#111216;border-radius:7px;margin:10px 0}.hint{color:#a8abb2;line-height:1.5}.effect{color:#f4d35e;font-weight:600;margin:12px 0}.error{color:#ff7474}
@media(max-width:850px){main{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr) auto}aside{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mapping{height:130px}}
</style></head><body><header><div class="brand">XLeRobot Teleoperation</div>
<span><i id="sshDot" class="dot"></i>SSH</span><span><i id="leaderDot" class="dot"></i>Leaders</span><span><i id="videoDot" class="dot"></i>Video</span><div class="grow"></div>
<select id="profile"><option value="direct">Direct</option><option value="mirrored">Mirrored · invert base rotation</option></select>
<button id="start" class="primary">Start</button><button id="save">Save Sample</button><button onclick="document.documentElement.requestFullscreen()">Fullscreen</button></header>
<main><div class="viewer"><img id="frame" alt="Waiting for simulator video"></div><aside>
<div class="label">Control mapping</div><svg id="map" class="mapping" viewBox="0 0 270 190"></svg><div id="effect" class="effect"></div>
<div class="label">Session</div><div id="status" class="hint">Connecting…</div><p class="hint">Choose the mapping while paused. The new mode anchors at the leaders’ current pose, then press Start.</p>
</aside></main><script>
const profile=document.getElementById('profile'),start=document.getElementById('start'),save=document.getElementById('save'),statusEl=document.getElementById('status'),frame=document.getElementById('frame');
let frameId=-1;
function diagram(v){const mirrored=v==='mirrored';const a='M70 55 L70 135 M200 55 L200 135';document.getElementById('map').innerHTML=`<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#f4d35e"/></marker></defs><text x="48" y="30" fill="#aaa">Leader L</text><text x="176" y="30" fill="#aaa">Leader R</text><circle cx="70" cy="50" r="14" fill="#30343b"/><circle cx="200" cy="50" r="14" fill="#30343b"/><path d="${a}" stroke="#f4d35e" stroke-width="3" fill="none" marker-end="url(#a)"/><circle cx="70" cy="140" r="14" fill="#235c42"/><circle cx="200" cy="140" r="14" fill="#235c42"/><text x="40" y="174" fill="#aaa">Follower L</text><text x="168" y="174" fill="#aaa">Follower R</text>`;document.getElementById('effect').textContent='Left → Left, Right → Right. '+(mirrored?'Base rotation and wrist roll are inverted; joints 2–4 and gripper follow directly.':'All six joints follow directly.');}
async function post(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok)throw new Error(await r.text());return r.json();}
profile.onchange=async()=>{try{await post('/api/orientation',{profile:profile.value});diagram(profile.value)}catch(e){statusEl.textContent=e.message;statusEl.className='error'}};
start.onclick=async()=>{try{start.disabled=true;start.innerHTML='<i class="spin"></i>Starting…';await post('/api/control',{command:'start_pause'});}catch(e){start.disabled=false;start.textContent='Start';statusEl.textContent=e.message;statusEl.className='error'}};
save.onclick=async()=>{try{save.disabled=true;save.innerHTML='<i class="spin"></i>Saving…';await post('/api/control',{command:'save'});}catch(e){save.disabled=false;save.textContent='Save Sample';statusEl.textContent=e.message;statusEl.className='error'}};
async function poll(){try{const s=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json());for(const [id,key] of [['sshDot','ssh_connected'],['leaderDot','leaders_connected'],['videoDot','video_connected']])document.getElementById(id).className='dot '+(s[key]?'on':'');profile.value=s.control_profile;diagram(s.control_profile);statusEl.textContent=s.status;statusEl.className=s.remote_state==='DISCONNECTED'?'error':'hint';const rs=s.remote_state;save.disabled=rs!=='RECORDING'||s.command_pending;save.textContent='Save Sample';if(s.command_pending){start.disabled=true;start.innerHTML='<i class="spin"></i>'+(s.command_target==='PAUSED'?'Finishing…':'Starting…');}else if(rs==='RECORDING'){start.disabled=false;start.textContent='Pause';}else if(rs==='RESTORING'||rs==='BOOTING'){start.disabled=true;start.innerHTML='<i class="spin"></i>Loading…';}else if(rs==='DISCONNECTED'){start.disabled=true;start.textContent='Disconnected';}else{start.disabled=false;start.textContent='Start';}if(s.frame_id!==frameId){frameId=s.frame_id;frame.src='/api/frame.jpg?id='+frameId}}catch(e){statusEl.textContent='Gateway disconnected';statusEl.className='error'}setTimeout(poll,300)}diagram(profile.value);poll();
</script></body></html>"""


class State:
    def __init__(self, control_profile="direct"):
        self.lock = threading.Lock()
        self.frame = b""
        self.frame_id = 0
        self.leaders_connected = False
        self.video_connected = False
        self.ssh_connected = False
        self.control_profile = control_profile
        self.remote_state = "BOOTING"
        self.command_pending = False
        self.command_sent_at = None
        self.command_target = None
        self.command_delivered_at = None
        self.status = "Connecting to persistent RunPod session..."
        self.keys: queue.SimpleQueue[int] = queue.SimpleQueue()
        self.stop = threading.Event()

    def clear_keys(self):
        while True:
            try:
                self.keys.get_nowait()
            except queue.Empty:
                return

    def snapshot(self):
        with self.lock:
            return {
                "frame_id": self.frame_id,
                "leaders_connected": self.leaders_connected,
                "video_connected": self.video_connected,
                "ssh_connected": self.ssh_connected,
                "control_profile": self.control_profile,
                "remote_state": self.remote_state,
                "command_pending": self.command_pending,
                "command_target": self.command_target,
                "command_delivered": self.command_delivered_at is not None,
                "status": self.status,
            }


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
                name: Motor(index, "sts3215", MotorNormMode.RANGE_0_100 if name == "gripper" else MotorNormMode.DEGREES)
                for index, name in enumerate(MOTOR_NAMES, 1)
            }
            bus = FeetechMotorsBus(port=port, motors=motors, calibration=calibration)
            bus.connect(); bus.disable_torque()
            return bus

        self.left = make_bus(left_port, calibration_dir / "aurochs_xlerobot_leaders_left.json")
        self.right = make_bus(right_port, calibration_dir / "aurochs_xlerobot_leaders_right.json")

    def read(self):
        return {"left": self.left.sync_read("Present_Position", num_retry=2), "right": self.right.sync_read("Present_Position", num_retry=2), "ts": time.time()}

    def close(self):
        for bus in (self.left, self.right):
            try: bus.disable_torque()
            finally: bus.disconnect()


def listener(port: int):
    sock = socket.socket(); sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port)); sock.listen(1); sock.settimeout(1)
    return sock


def serve_leaders(sock, leaders, state):
    while not state.stop.is_set():
        try: conn, _ = sock.accept()
        except socket.timeout: continue
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with state.lock: state.leaders_connected = True
            try:
                conn.sendall(b'{"status":"ready"}\n')
                while not state.stop.is_set():
                    started = time.monotonic(); payload = leaders.read()
                    with state.lock: payload["control_profile"] = state.control_profile
                    conn.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode())
                    state.stop.wait(max(0.0, 1 / 30 - (time.monotonic() - started)))
            except (ConnectionError, OSError): pass
            finally:
                with state.lock: state.leaders_connected = False


def recv_exact(conn, size):
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk: raise ConnectionError("socket closed")
        data.extend(chunk)
    return bytes(data)


def serve_video(sock, state):
    while not state.stop.is_set():
        try: conn, _ = sock.accept()
        except socket.timeout: continue
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with state.lock:
                state.video_connected = True; state.status = "Ready — choose mapping, then Start"
            try:
                while not state.stop.is_set():
                    payload = recv_exact(conn, struct.unpack("!I", recv_exact(conn, 4))[0])
                    metadata_raw, separator, frame = payload.partition(b"\n")
                    metadata = json.loads(metadata_raw) if separator else {}
                    with state.lock:
                        previous_state = state.remote_state
                        remote_state = metadata.get("ui_state", state.remote_state)
                        state.remote_state = remote_state
                        if state.command_pending and remote_state == state.command_target:
                            state.command_pending = False
                            elapsed = time.monotonic() - state.command_sent_at if state.command_sent_at else 0
                            state.status = f"{remote_state.title()} — simulator acknowledged in {elapsed:.1f}s"
                        elif not state.command_pending and remote_state != previous_state:
                            state.status = {
                                "PAUSED": "Ready — controls paused",
                                "RECORDING": "Recording — controls active",
                                "RESTORING": "Loading simulator state…",
                            }.get(remote_state, remote_state.title())
                        state.frame = frame; state.frame_id += 1
                    try: key = state.keys.get_nowait()
                    except queue.Empty: key = -1
                    if key >= 0:
                        with state.lock:
                            state.command_delivered_at = time.monotonic()
                            elapsed = state.command_delivered_at - state.command_sent_at
                            state.status = f"Command delivered in {elapsed:.1f}s — simulator is activating…"
                    conn.sendall(struct.pack("!i", key))
            except (ConnectionError, OSError): pass
            finally:
                state.clear_keys()
                with state.lock:
                    state.video_connected = False; state.frame = b""
                    state.remote_state = "DISCONNECTED"
                    state.command_pending = False
                    state.status = "Simulator disconnected — restart or reconnect required"


def supervise_ssh(args, state):
    command = ["ssh", "-i", str(args.ssh_key), "-p", str(args.ssh_port), "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-R", f"127.0.0.1:{args.action_port}:127.0.0.1:{args.action_port}", "-R", f"127.0.0.1:{args.video_port}:127.0.0.1:{args.video_port}", f"root@{args.ssh_host}", args.remote_command]
    while not state.stop.is_set():
        proc = subprocess.Popen(command)
        with state.lock: state.ssh_connected = True
        while proc.poll() is None and not state.stop.wait(.5): pass
        if state.stop.is_set() and proc.poll() is None: proc.terminate()
        with state.lock: state.ssh_connected = False; state.status = "SSH disconnected — reconnecting..."
        state.stop.wait(2)


def handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/": return self.send(HTML.encode(), "text/html; charset=utf-8")
            if path == "/api/status": return self.send(json.dumps(state.snapshot()).encode(), "application/json")
            if path == "/api/frame.jpg":
                with state.lock: frame = state.frame
                return self.send(frame or b"no frame", "image/jpeg" if frame else "text/plain", 200 if frame else 503)
            return self.send(b"not found", "text/plain", 404)

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except (ValueError, json.JSONDecodeError):
                return self.send(b"invalid JSON", "text/plain", 400)
            if self.path == "/api/orientation":
                profile = body.get("profile")
                if profile not in PROFILES: return self.send(b"unknown orientation", "text/plain", 400)
                with state.lock:
                    state.control_profile = profile; state.status = f"Selected {PROFILES[profile]} — anchored at current pose"
                return self.send(b'{"ok":true}', "application/json")
            if self.path == "/api/control":
                command = body.get("command")
                if command not in COMMANDS: return self.send(b"unknown command", "text/plain", 400)
                with state.lock: connected = state.video_connected
                if not connected: return self.send(b"simulator is reconnecting", "text/plain", 409)
                with state.lock:
                    state.command_pending = True
                    state.command_sent_at = time.monotonic()
                    state.command_target = "PAUSED" if command == "save" or state.remote_state == "RECORDING" else "RECORDING"
                    state.command_delivered_at = None
                    verb = "Save" if command == "save" else ("Pause" if state.command_target == "PAUSED" else "Start")
                    state.status = f"{verb} requested — waiting for simulator acknowledgement…"
                state.keys.put(COMMANDS[command]); return self.send(b'{"ok":true}', "application/json")
            return self.send(b"not found", "text/plain", 404)

        def send(self, body, content_type, status=200):
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
        def log_message(self, *_): pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-port", required=True); parser.add_argument("--right-port", required=True)
    parser.add_argument("--ssh-host", required=True); parser.add_argument("--ssh-port", required=True, type=int)
    parser.add_argument("--ssh-key", required=True, type=Path); parser.add_argument("--remote-command", required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/real_robot.yaml"))
    parser.add_argument("--calibration-dir", type=Path, default=Path.home() / ".cache/huggingface/lerobot/calibration/teleoperators/so_leader")
    parser.add_argument("--action-port", type=int, default=18765); parser.add_argument("--video-port", type=int, default=18766); parser.add_argument("--http-port", type=int, default=4174)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    try:
        profile = get_control_profile(config)
    except ValueError as exc:
        parser.error(str(exc))
    state = State(profile); leaders = LeaderReader(args.left_port, args.right_port, args.calibration_dir)
    action_sock, video_sock = listener(args.action_port), listener(args.video_port)
    threading.Thread(target=serve_leaders, args=(action_sock, leaders, state), daemon=True).start()
    threading.Thread(target=serve_video, args=(video_sock, state), daemon=True).start()
    threading.Thread(target=supervise_ssh, args=(args, state), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), handler(state))
    threading.Timer(.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.http_port}")).start()
    print(f"XLeRobot controls: http://127.0.0.1:{args.http_port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        state.stop.set(); server.server_close(); action_sock.close(); video_sock.close(); leaders.close()


if __name__ == "__main__": main()
