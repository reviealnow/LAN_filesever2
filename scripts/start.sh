#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# Bootstrap and launch the LAN File Server with one command.
#
#   ./scripts/start.sh
#
# It will: create a virtualenv, install dependencies, generate a persistent
# SECRET_KEY (so logins survive restarts), print the LAN address, and start
# the HTTPS server. Safe to re-run — each step is idempotent.
#
# Environment overrides:
#   PORT=8443         port to listen on
#   HOST=0.0.0.0      bind address (0.0.0.0 = reachable on the LAN)
#   FLASK_DEBUG=0     set to 1 for the dev reloader/debugger (NOT on a shared LAN)
#   SECRET_KEY=...    use an explicit key instead of the generated one
#   SSL_CERT_FILE / SSL_KEY_FILE   use real certs instead of the self-signed one
# ---------------------------------------------------------------------------
set -eu

# Resolve repo root (this script lives in scripts/).
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

PORT="${PORT:-8443}"
HOST="${HOST:-0.0.0.0}"
FLASK_DEBUG="${FLASK_DEBUG:-0}"
export PORT HOST FLASK_DEBUG

# 1. Require python3.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found on PATH." >&2
  exit 1
fi

# 2. Create the virtualenv on first run.
if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

# 3. Install / update dependencies (quiet, idempotent).
echo "==> Installing dependencies"
python -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
python -m pip install --quiet -r requirements.txt

# 4. Persistent SECRET_KEY so sessions survive restarts.
#    (app.py falls back to a random per-process key if this is unset.)
if [ -z "${SECRET_KEY:-}" ]; then
  if [ ! -f ".secret_key" ]; then
    python -c "import secrets; print(secrets.token_hex(32))" > .secret_key
    chmod 600 .secret_key 2>/dev/null || true
    echo "==> Generated a persistent SECRET_KEY (.secret_key)"
  fi
  SECRET_KEY=$(cat .secret_key)
  export SECRET_KEY
fi

# 5. Work out the LAN address to share with other machines.
LAN_IP=$(python - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
except Exception:
    print("127.0.0.1")
finally:
    s.close()
PY
)

echo ""
echo "==> LAN File Server starting"
echo "    Local:   https://localhost:${PORT}"
echo "    Network: https://${LAN_IP}:${PORT}"
echo "    (self-signed certificate — accept the browser warning on first visit)"
echo "    Press Ctrl+C to stop."
echo ""

# 6. Launch (HTTPS adhoc unless SSL_CERT_FILE/SSL_KEY_FILE are set).
exec python app.py
