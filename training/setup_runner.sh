#!/usr/bin/env bash
# One-time setup for VAPE's GPU training box — installs the Python/CUDA
# stack this repo's training/ scripts need, then registers the box as a
# self-hosted GitHub Actions runner so .github/workflows/train-vape-model.yml
# can dispatch training/eval jobs onto it (same operational pattern already
# used for every other workflow this session — dispatch, read logs).
#
# Run this ONCE per GPU box (Oracle GPU shape, GCP GPU VM, or any Ubuntu
# 22.04+ box with an NVIDIA GPU and a driver already installed by the cloud
# image — this script does NOT install GPU drivers itself, since that's
# image/provider-specific and this box came from a cloud marketplace image
# that almost always ships one already).
#
# Usage:
#   1. In the V.A.P.E repo on GitHub: Settings -> Actions -> Runners ->
#      New self-hosted runner -> Linux. Copy the registration TOKEN it shows
#      you (it's short-lived — grab it right before running this script).
#   2. On the GPU box:
#        curl -fsSL https://raw.githubusercontent.com/<owner>/V.A.P.E/<branch>/training/setup_runner.sh -o setup_runner.sh
#        chmod +x setup_runner.sh
#        ./setup_runner.sh <REPO_URL> <REGISTRATION_TOKEN> [RUNNER_LABEL]
#      e.g. ./setup_runner.sh https://github.com/jUXTAPOSITION1/V.A.P.E ABCDEF123... gpu-train
#
# After this completes, add the runner's label (default: gpu-train) to
# .github/workflows/train-vape-model.yml's `runs-on:` if you changed it, and
# add HF_TOKEN (a Hugging Face access token with the chosen Gemma
# checkpoint's license accepted) as a repo secret before dispatching the
# training workflow.
set -euo pipefail

REPO_URL="${1:?usage: setup_runner.sh <REPO_URL> <REGISTRATION_TOKEN> [RUNNER_LABEL]}"
REG_TOKEN="${2:?usage: setup_runner.sh <REPO_URL> <REGISTRATION_TOKEN> [RUNNER_LABEL]}"
RUNNER_LABEL="${3:-gpu-train}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner}"
RUNNER_VERSION="${RUNNER_VERSION:-2.319.1}"  # verify this is still current at https://github.com/actions/runner/releases before running

echo "=== 1. Sanity-check the GPU is actually visible ==="
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found. This box either has no GPU attached, or the" >&2
  echo "cloud image's NVIDIA driver isn't installed. Fix that first — this" >&2
  echo "script deliberately does not attempt to install GPU drivers itself" >&2
  echo "(too provider/image-specific to get right generically)." >&2
  exit 1
fi
nvidia-smi

echo "=== 2. Python + venv for training/ deps ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl jq

VENV_DIR="$HOME/vape-training-venv"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

echo "=== 3. Clone the repo (for training/requirements.txt) ==="
REPO_DIR="$HOME/V.A.P.E"
if [ ! -d "$REPO_DIR" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
fi
pip install -r "$REPO_DIR/training/requirements.txt"

echo "=== 4. Download + configure the GitHub Actions self-hosted runner ==="
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"
if [ ! -f "./config.sh" ]; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64) RUNNER_ARCH="x64" ;;
    aarch64|arm64) RUNNER_ARCH="arm64" ;;
    *) echo "Unrecognized architecture $ARCH — check https://github.com/actions/runner/releases for the right asset name." >&2; exit 1 ;;
  esac
  PKG="actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
  curl -fsSL -o "$PKG" "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${PKG}"
  tar xzf "$PKG"
fi

./config.sh --url "$REPO_URL" --token "$REG_TOKEN" --labels "$RUNNER_LABEL" --unattended --replace

echo "=== 5. Install + start the runner as a systemd service ==="
sudo ./svc.sh install
sudo ./svc.sh start

echo ""
echo "Done. Runner label: $RUNNER_LABEL"
echo "Virtualenv (training deps): $VENV_DIR"
echo "Repo clone: $REPO_DIR"
echo ""
echo "Next: confirm this runner shows 'Idle' at"
echo "  ${REPO_URL}/settings/actions/runners"
echo "then dispatch .github/workflows/train-vape-model.yml."
