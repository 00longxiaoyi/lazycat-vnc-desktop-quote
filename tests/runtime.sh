#!/bin/bash
# Container-only check. Requires a built image, Docker and host Python 3.
# Returns nonzero if the actual quotation window cannot start (e.g. QEMU).
set -euo pipefail
image=${1:-quote-desktop-vnc:1.0.0}
arch=$(docker info --format '{{.Architecture}}')
if [[ "$arch" != x86_64 && "$arch" != amd64 && ${ALLOW_EMULATION:-0} != 1 ]]; then
    echo 'Use a native amd64 Docker host; QEMU Electron tests can exhaust memory.' >&2
    echo 'Set ALLOW_EMULATION=1 only to reproduce the known failure (container limited to 2 GiB).' >&2
    exit 2
fi
root=$(cd "$(dirname "$0")/.." && pwd)
logdir="$root/validation"
mkdir -p "$logdir"
name="quote-vnc-check-$$"
volume="$name-data"
cleanup() {
    docker rm -f "$name" >/dev/null 2>&1 || true
    docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker volume create "$volume" >/dev/null
# Simulate lzcos run_as owner mapping; never chmod 777 the data.
docker run --rm --platform linux/amd64 --user root --entrypoint /bin/chown \
    -v "$volume:/lzcapp/var" "$image" 1000:1000 /lzcapp/var
start() {
    docker run -d --platform linux/amd64 --name "$name" --memory 2g --shm-size 512m --ulimit core=0 \
        -e LAZYCAT_APP_DEPLOY_UID="$1" \
        -p 127.0.0.1::6901 -v "$volume:/lzcapp/var" "$image" >/dev/null
    for i in $(seq 1 60); do
        if docker exec "$name" test -f "/lzcapp/var/users/$1/startup.log"; then
            echo "PASS: XFCE invoked start-quote automatically for $1"
            return
        fi
        sleep 1
    done
    docker logs "$name" >"$logdir/container-failure.log" 2>&1
    echo 'FAIL: XFCE autostart did not execute' >&2
    exit 1
}
start test-user
port=$(docker port "$name" 6901/tcp | sed 's/.*://')
python3 - "$port" <<'PY'
import socket,sys,urllib.request
port=int(sys.argv[1])
assert urllib.request.urlopen(f'http://127.0.0.1:{port}/').status == 200
with socket.create_connection(('127.0.0.1',port),timeout=5) as s:
    s.sendall((f'GET /websockify HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
      f'Origin: http://127.0.0.1:{port}\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n'
      'Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n'
      'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n').encode())
    assert b'101 Switching Protocols' in s.recv(1024)
print('PASS: VNC HTTP 200 and WebSocket 101 (no direct-port auth; Lazycat must gate it)')
PY
sleep 10
status=0
if docker exec "$name" sh -c 'xwininfo -root -tree | grep -q "报价系统（桌面版）"'; then
    echo 'PASS: actual Electron quotation window is visible'
else
    echo 'FAIL: actual Electron quotation window absent; inspect startup log'
    status=1
fi
docker exec "$name" cat /lzcapp/var/users/test-user/startup.log >"$logdir/electron-startup.log"
docker logs "$name" >"$logdir/container.log" 2>&1
# Fixtures test the storage contract, NOT successful app-level save/load.
docker exec "$name" sh -eu -c '
    d=/lzcapp/var/users/test-user
    mkdir -p "$d/quote-desktop/files/test-instrument/specFiles"
    printf "persist-business\n" > "$d/quote-desktop/persistence-test.json"
    printf "persist-attachment\n" > "$d/quote-desktop/files/test-instrument/specFiles/fixture.txt"
    printf "persist-export\n" > "$d/exports/fixture.txt"
    test "$(stat -c %u:%g "$d/quote-desktop")" = 1000:1000
    test "$(readlink "$HOME/Downloads")" = "$d/exports"
'
docker rm -f "$name" >/dev/null
start test-user
docker exec "$name" sh -eu -c '
    d=/lzcapp/var/users/test-user
    test "$(cat "$d/quote-desktop/persistence-test.json")" = persist-business
    test "$(cat "$d/quote-desktop/files/test-instrument/specFiles/fixture.txt")" = persist-attachment
    test "$(cat "$d/exports/fixture.txt")" = persist-export
'
echo 'PASS: data/attachment/export fixtures survive container deletion and recreation'
docker rm -f "$name" >/dev/null
start other-user
docker exec "$name" sh -eu -c '
    d=/lzcapp/var/users/other-user
    test -d "$d/quote-desktop"
    test ! -e "$d/quote-desktop/persistence-test.json"
    test ! -e "$d/exports/fixture.txt"
    test "$(readlink "$HOME/Downloads")" = "$d/exports"
'
echo 'PASS: another deployment UID selects different business/export directories'
exit "$status"
