#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
if [[ -f "$repo_root/.env.teleop" ]]; then
  set -a
  source "$repo_root/.env.teleop"
  set +a
fi

command_name=${1:-attach}
python=${LOCAL_LEROBOT_PYTHON:-$repo_root/../lerobot-teleop/.venv-seeed/bin/python}
ssh_key=${RUNPOD_SSH_KEY:-$HOME/.runpod/ssh/runpodctl-ssh-key}
service_dir=/workspace/lehome/task0003/persistent-teleop
service_pid=$service_dir/service.pid
service_log=$service_dir/service.log

: "${RUNPOD_SSH_HOST:?Set RUNPOD_SSH_HOST in .env.teleop}"
: "${RUNPOD_SSH_PORT:?Set RUNPOD_SSH_PORT in .env.teleop}"

ssh_remote() {
  ssh -i "$ssh_key" -p "$RUNPOD_SSH_PORT" -o BatchMode=yes \
    -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "root@$RUNPOD_SSH_HOST" "$@"
}

status_command="pid=\$(cat '$service_pid' 2>/dev/null || true); if test -n \"\$pid\" && kill -0 \"\$pid\" 2>/dev/null; then if tail -n 30 '$service_log' | grep -q 'Simulation App Shutting Down'; then phase=failed; elif grep -q 'Ready:' '$service_log'; then phase=ready; elif grep -q 'Booting sim' '$service_log'; then phase=booting; else phase=starting; fi; child=\$(pgrep -P \"\$pid\" | head -1); printf 'wrapper=running phase=%s pid=%s child=%s\\n' \"\$phase\" \"\$pid\" \"\${child:-none}\"; if test -n \"\$child\"; then ps -p \"\$child\" -o etime=,stat=,%cpu=,cmd=; fi; tail -n 4 '$service_log'; else echo 'wrapper=stopped phase=stopped'; fi"
stop_command="pid=\$(cat '$service_pid' 2>/dev/null || true); if test -n \"\$pid\" && kill -0 \"\$pid\" 2>/dev/null; then kill -TERM -- -\"\$pid\" 2>/dev/null || kill \"\$pid\" 2>/dev/null || true; fi; rm -f '$service_pid'; echo 'persistent simulator stopped'"
start_command="mkdir -p '$service_dir'; run_id=\$(date -u +%Y%m%dT%H%M%SZ); output='$service_dir'/session_\$run_id; : >'$service_log'; cd /workspace/lehome/solution; nohup setsid env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 XLEROBOT_CONTROL_PROFILE=operator_cartesian_mirror XLEROBOT_AUTO_START=0 uv run python /workspace/lehome/task0003/remote_dagger_tcp.py --random_garment Top_Short_Seen_0 --output_dir \"\$output\" --num_episodes 9999 --num_sims 1 --camera_width 320 --camera_height 240 --render_every_n 3 --episode_timeout 600 >>'$service_log' 2>&1 </dev/null & echo \$! >'$service_pid'; echo \"persistent simulator starting pid=\$! output=\$output\""

case "$command_name" in
  status)
    ssh_remote "$status_command"
    ;;
  stop)
    ssh_remote "$stop_command"
    ;;
  restart)
    ssh_remote "$stop_command; $start_command"
    ;;
  attach)
    : "${LEFT_LEADER_PORT:?Set LEFT_LEADER_PORT in .env.teleop}"
    : "${RIGHT_LEADER_PORT:?Set RIGHT_LEADER_PORT in .env.teleop}"
    for path in "$python" "$LEFT_LEADER_PORT" "$RIGHT_LEADER_PORT" "$ssh_key"; do
      if [[ ! -e "$path" ]]; then
        echo "Missing required path: $path" >&2
        exit 1
      fi
    done
    if ! ssh_remote "$status_command" | grep -q 'wrapper=running'; then
      ssh_remote "$start_command"
    fi
    remote_command="echo 'Attached to persistent simulator'; tail -n 20 -F '$service_log'"
    exec "$python" "$repo_root/scripts/teleop_gateway.py" \
      --left-port "$LEFT_LEADER_PORT" --right-port "$RIGHT_LEADER_PORT" \
      --ssh-host "$RUNPOD_SSH_HOST" --ssh-port "$RUNPOD_SSH_PORT" \
      --ssh-key "$ssh_key" --remote-command "$remote_command"
    ;;
  *)
    echo "Usage: $0 {attach|status|restart|stop}" >&2
    exit 2
    ;;
esac
