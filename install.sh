#!/bin/sh
# Install clive — CLI for Ethereum Hive test results
# Usage: curl -LsSf https://raw.githubusercontent.com/spencer-tb/clive/main/install.sh | sh
set -eu

REPO="spencer-tb/clive"
BINARY="clive"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

get_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "darwin" ;;
        *)       echo "unsupported" ;;
    esac
}

get_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        *)             echo "unsupported" ;;
    esac
}

main() {
    OS=$(get_os)
    ARCH=$(get_arch)

    if [ "$OS" = "unsupported" ] || [ "$ARCH" = "unsupported" ]; then
        echo "error: unsupported platform $(uname -s)/$(uname -m)" >&2
        exit 1
    fi

    ASSET="${BINARY}-${OS}-${ARCH}"

    # Get latest release tag
    TAG=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    if [ -z "$TAG" ]; then
        echo "error: could not find latest release" >&2
        exit 1
    fi

    URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"

    echo "Installing ${BINARY} ${TAG} (${OS}/${ARCH})..."

    mkdir -p "$INSTALL_DIR"
    curl -fsSL "$URL" -o "${INSTALL_DIR}/${BINARY}"
    chmod +x "${INSTALL_DIR}/${BINARY}"

    echo "Installed to ${INSTALL_DIR}/${BINARY}"

    # Check if INSTALL_DIR is on PATH
    case ":$PATH:" in
        *":${INSTALL_DIR}:"*) ;;
        *)
            echo ""
            echo "Add to your PATH:"
            echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
            ;;
    esac
}

main
