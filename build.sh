#!/usr/bin/env bash
# build.sh — Clone all SCION-IPFS dependencies and build the SCION-enabled IPFS binary.
#
# Output layout under release/:
#   release/
#   ├── go-libp2p/   netsys-lab fork (feature/scion-quic-transport)
#   ├── boxo/        netsys-lab fork (feature/scion-boxo)
#   ├── kubo/        ipfs/kubo (IPFS reference implementation)
#   └── ipfs         compiled binary

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GO_LIBP2P_REPO="https://github.com/netsys-lab/go-libp2p.git"
GO_LIBP2P_BRANCH="feature/scion-quic-transport"

BOXO_REPO="https://github.com/netsys-lab/boxo.git"
BOXO_BRANCH="feature/scion-boxo"

KUBO_REPO="https://github.com/netsys-lab/kubo.git"
KUBO_TAG="feature/scion-v0.12.0"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$SCRIPT_DIR/release"

GO_LIBP2P_DIR="$RELEASE_DIR/go-libp2p"
BOXO_DIR="$RELEASE_DIR/boxo"
KUBO_DIR="$RELEASE_DIR/kubo"
OUTPUT_BIN="$RELEASE_DIR/ipfs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[build]${NC} $*"; }
warn() { echo -e "${YELLOW}[ warn]${NC} $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

clone_or_update() {
    local label="$1" url="$2" dir="$3" ref="$4"
    if [[ -d "$dir/.git" ]]; then
        log "Updating $label …"
        git -C "$dir" fetch --quiet origin
        git -C "$dir" checkout --quiet "$ref"
        git -C "$dir" pull  --quiet origin "$ref"
    else
        log "Cloning $label ($ref) …"
        git clone --quiet --branch "$ref" --depth 1 "$url" "$dir"
    fi
}

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
for cmd in go git; do
    command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' not found — please install it first."
done

GO_MAJOR=$(go version | awk '{print $3}' | sed 's/go//' | cut -d. -f1)
GO_MINOR=$(go version | awk '{print $3}' | sed 's/go//' | cut -d. -f2)
if [[ "$GO_MAJOR" -lt 1 || ( "$GO_MAJOR" -eq 1 && "$GO_MINOR" -lt 21 ) ]]; then
    die "Go 1.21+ is required (found $(go version))."
fi

# ---------------------------------------------------------------------------
# Step 1: Create release directory
# ---------------------------------------------------------------------------
log "Creating release/ directory …"
mkdir -p "$RELEASE_DIR"

# ---------------------------------------------------------------------------
# Step 2: Clone / update the SCION-extended forks
# ---------------------------------------------------------------------------
clone_or_update "go-libp2p (SCION transport + PILA)" \
    "$GO_LIBP2P_REPO" "$GO_LIBP2P_DIR" "$GO_LIBP2P_BRANCH"

clone_or_update "boxo (path selection strategies)" \
    "$BOXO_REPO" "$BOXO_DIR" "$BOXO_BRANCH"

# ---------------------------------------------------------------------------
# Step 3: Clone / update Kubo (IPFS reference implementation)
# ---------------------------------------------------------------------------
clone_or_update "kubo (IPFS)" "$KUBO_REPO" "$KUBO_DIR" "$KUBO_TAG"

# ---------------------------------------------------------------------------
# Step 4: Inject replace directives into kubo's go.mod
# ---------------------------------------------------------------------------
log "Patching kubo/go.mod with local replace directives …"
cd "$KUBO_DIR"

# Drop any previous run's replaces to stay idempotent.
go mod edit -dropreplace=github.com/libp2p/go-libp2p 2>/dev/null || true
go mod edit -dropreplace=github.com/ipfs/boxo        2>/dev/null || true

# Point kubo at our local SCION forks (paths are relative to kubo/).
go mod edit -replace "github.com/libp2p/go-libp2p=../go-libp2p"
go mod edit -replace "github.com/ipfs/boxo=../boxo"

log "go.mod replace directives:"
grep "^replace" go.mod | grep -E "go-libp2p|boxo" | sed 's/^/  /'

# ---------------------------------------------------------------------------
# Step 5: Resolve dependencies
# ---------------------------------------------------------------------------
log "Running 'go mod tidy' (this may take a minute) …"
if ! go mod tidy 2>&1; then
    warn "'go mod tidy' encountered errors."
    warn "Check that the go-libp2p and boxo fork branches are compatible with"
    warn "netsys-lab/kubo@$KUBO_TAG (inspect each fork's go.mod for version hints)."
    die "Dependency resolution failed — cannot continue."
fi

# ---------------------------------------------------------------------------
# Step 6: Build the IPFS binary
# ---------------------------------------------------------------------------
log "Building IPFS binary with SCION support …"
go build -v \
    -ldflags="-X github.com/ipfs/kubo/repo/fsrepo.CurrentCommit=$(git -C "$KUBO_DIR" rev-parse --short HEAD)" \
    -o "$OUTPUT_BIN" \
    ./cmd/ipfs

# ---------------------------------------------------------------------------
# Step 7: Sanity-check the binary
# ---------------------------------------------------------------------------
log "Verifying binary …"
"$OUTPUT_BIN" version --all

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
log "Build complete."
echo ""
echo "  Binary  : $OUTPUT_BIN"
echo "  Version : $("$OUTPUT_BIN" version)"
echo ""
echo "  Runtime configuration (set before running the node):"
echo "    export SCION_PILA_URL=\"http://localhost:8080\"      # PILA cert service"
echo "    export SCION_PILA_CERTS_FOLDER=\"/etc/scion/certs\" # TRC verification certs"
echo ""
echo "  Start the node:"
echo "    $OUTPUT_BIN init"
echo "    $OUTPUT_BIN daemon"
