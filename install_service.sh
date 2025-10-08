#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# install_service.sh
# ---------------------------------------------------------------------------
# This script installs the Radio Recorder Web UI as a systemd service so that
# it can automatically start at boot.  It creates a Python virtual environment,
# installs the application's dependencies, and registers a systemd unit that
# launches the Flask development server on port 5000.  Run this script with
# root privileges (for example via `sudo`) from the repository root.
# ---------------------------------------------------------------------------

set -euo pipefail

# Print helpful output describing every major step that is about to occur.  The
# `set -x` flag is intentionally avoided to keep the logs readable; instead we
# echo the actions we perform ourselves.

# Function: print a banner for a new step so the logs are easy to read.
print_step() {
  local message="$1"
  echo
  echo "==> ${message}"
}

# Verify that the script is running with root privileges because we need to
# install files under /etc/systemd/system.  `id -u` returns the numeric user ID
# of the current process; the root user always has ID 0.
if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must be run as root (e.g. 'sudo ./install_service.sh')." >&2
  exit 1
fi

print_step "Detecting installation context"

# `BASH_SOURCE[0]` points at the path to this script, even when the script is
# invoked via a symbolic link.  We use it to locate the repository root.
SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"

# We install the virtual environment inside the repository to keep everything
# self-contained.  Feel free to adjust this path if you prefer a different
# layout.
VENV_DIR="${REPO_DIR}/.venv"

# Determine which non-root user should run the service.  When the script is
# invoked with sudo, the SUDO_USER environment variable points to the
# originating user.  If SUDO_USER is empty (e.g., the script was run as root
# directly), we fall back to the current user name.
SERVICE_USER="${SUDO_USER:-$(id -un)}"
SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"

# The systemd unit will be registered under this name.  You can change the
# value if you want a custom service identifier.
SERVICE_NAME="radio-recorder-web-ui"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

print_step "Ensuring Python 3 is available"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required but was not found in PATH." >&2
  exit 1
fi

print_step "Creating virtual environment at ${VENV_DIR}"

# Only create the virtual environment if it does not already exist.  This makes
# the script idempotent; re-running it will reuse the existing environment.
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
else
  echo "Virtual environment already exists; skipping creation."
fi

print_step "Installing Python dependencies"

# Upgrade pip to ensure we can install modern wheels and then install the
# dependencies defined in requirements.txt.  The --requirement flag instructs
# pip to read package names from the file.
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install --requirement "${REPO_DIR}/requirements.txt"

print_step "Writing systemd service file to ${SERVICE_FILE}"

# The systemd unit file specifies how the application should be launched.  The
# Environment directive prepends the virtual environment's bin directory to the
# PATH so that the `flask` command resolves to the version inside the venv.
# Using Restart=on-failure causes systemd to automatically restart the service
# if it exits unexpectedly.
cat <<UNIT | tee "${SERVICE_FILE}" >/dev/null
[Unit]
Description=Radio Recorder Web UI
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO_DIR}
Environment=PATH=${VENV_DIR}/bin
ExecStart=${VENV_DIR}/bin/flask --app app run --host=0.0.0.0 --port=5000
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

print_step "Reloading systemd and enabling the service"

# systemctl daemon-reload makes systemd aware of the new unit file.  The enable
# command configures the service to start at boot, and start launches it
# immediately so the application becomes available without a reboot.
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

print_step "Installation complete"

echo "The Radio Recorder Web UI should now be accessible on port 5000."
