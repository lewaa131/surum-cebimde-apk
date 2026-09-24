#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/WSL 22.04/24.04 helper for building the debug APK.
# Run this from the project folder inside the Linux filesystem (e.g. ~/suru-takip-android),
# not directly under /mnt/c.

sudo apt-get update
sudo apt-get install -y \
  git zip unzip openjdk-17-jdk python3 python3-pip python3-venv \
  autoconf automake autopoint gettext libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev ccache

python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install "Cython==0.29.34" legacy-cgi
python -m pip install "git+https://github.com/kivy/buildozer.git"

buildozer -v android debug

echo
echo "APK hazırsa bin/ klasöründe göreceksin:"
ls -lh bin/*.apk
