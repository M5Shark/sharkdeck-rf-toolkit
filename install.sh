#!/usr/bin/env bash
# ==========================================================
# Sharkdeck RF Toolkit - installer
# Target: WalnutPi / Allwinner H616, Debian 12 (bookworm)
#
# Builds the libgpiod v1.6 Python bindings that Adafruit
# Blinka needs, fixes the Debian site-packages/dist-packages
# path mismatch, and installs the Python deps.
#
# Usage:   bash install.sh
# ==========================================================
set -u

say()  { printf '\n\033[1;36m[*] %s\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m    %s\033[0m\n' "$1"; }
warn() { printf '\033[1;33m    %s\033[0m\n' "$1"; }
die()  { printf '\n\033[1;31m[!] %s\033[0m\n' "$1"; exit 1; }

PIP="pip3 install --break-system-packages --upgrade"

# ----------------------------------------------------------
say "1/5  Installing system build dependencies (sudo)"
sudo apt-get update || die "apt-get update failed"
sudo apt-get install -y git build-essential autoconf autoconf-archive \
    automake libtool pkg-config python3-dev python3-pip python3-setuptools m4 \
    || die "apt-get install failed"
ok "system deps installed"

# ----------------------------------------------------------
say "2/5  Installing Python packages (textual, blinka, nrf24)"
$PIP textual adafruit-blinka circuitpython-nrf24l01 \
  || pip3 install --upgrade textual adafruit-blinka circuitpython-nrf24l01 \
  || warn "pip install reported an error - continuing"
ok "python packages installed"

# ----------------------------------------------------------
say "3/5  Building libgpiod v1.6 Python bindings"
if python3 -c "import gpiod" 2>/dev/null; then
    ok "gpiod already importable - skipping build"
else
    SRC=/tmp/libgpiod-src
    rm -rf "$SRC"
    git clone https://github.com/brgl/libgpiod.git "$SRC" || die "git clone failed"
    cd "$SRC" || die "cannot cd into $SRC"
    git checkout v1.6.x || die "could not checkout v1.6.x branch"

    # autogen.sh in v1.6 only runs autoreconf; configure is run separately
    ./autogen.sh >/dev/null 2>&1 || true
    ./configure --enable-tools=yes --enable-bindings-python PYTHON=python3 \
        || die "configure failed (check python3-dev / setuptools)"
    make -j"$(nproc)" || die "make failed"
    sudo make install || die "make install failed"
    sudo ldconfig
    cd ~ || true
    ok "libgpiod built and installed"
fi

# ----------------------------------------------------------
say "4/5  Linking gpiod into Python's search path"
SO=$(find /usr/local/lib /usr/lib -name "gpiod*.so" 2>/dev/null | head -n1)
DIST=/usr/lib/python3/dist-packages
if [ -n "$SO" ]; then
    base=$(basename "$SO")
    if [ ! -e "$DIST/$base" ]; then
        sudo cp "$SO" "$DIST/" && ok "copied $base -> $DIST"
    else
        ok "module already present in $DIST"
    fi
else
    warn "no gpiod*.so found under /usr/local/lib - build may have skipped bindings"
fi

# ----------------------------------------------------------
say "5/5  Verifying the install"
if python3 -c "import gpiod; print('    gpiod OK', getattr(gpiod,'__version__','?'))"; then
    ok "gpiod imports correctly"
else
    die "gpiod still not importable - paste the output above for help"
fi

if python3 -c "import board" 2>/dev/null; then
    ok "board (Blinka) imports correctly"
else
    warn "import board failed - run 'python3 -c \"import board\"' and share the error"
fi

printf '\n\033[1;32m=== Done. Launch the app with:  python3 sharkdeck_app.py ===\033[0m\n\n'
