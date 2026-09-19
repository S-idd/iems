#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
VERSION=4.0.0-rc.1
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) PLATFORM=macos-arm64; EXPECTED=48a8331652ed95331bc5d9760fb612daff9165cd662a945470a8abd0cf0cf97d ;;
  Linux-x86_64) PLATFORM=linux-x64; EXPECTED=1a5e80bb22940295207aefbbe70511df8634044205ed98e3e6fcf2659ab08701 ;;
  *) echo 'Supported binary platforms: macOS ARM64, Linux x64.' >&2; exit 2 ;;
esac
ARCHIVE=${1:?Usage: scripts/dcg/install.sh /absolute/path/to/dcg-archive.tar.gz}
[[ -f "$ARCHIVE" ]] || { echo 'Archive not found.' >&2; exit 2; }
if command -v shasum >/dev/null; then
  ACTUAL=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
else
  ACTUAL=$(sha256sum "$ARCHIVE" | awk '{print $1}')
fi
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo 'Archive checksum does not match the pinned release.' >&2; exit 2; }
DEST="$ROOT/.dcg/runtime/dcg-$VERSION-$PLATFORM"
[[ ! -e "$DEST" ]] || { echo "Already installed: $DEST"; exit 0; }
umask 077
mkdir -p "$ROOT/.dcg/runtime"
STAGE=$(mktemp -d "$ROOT/.dcg/runtime/install.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT
tar -xzf "$ARCHIVE" -C "$STAGE"
(
  cd "$STAGE/dcg-$VERSION-$PLATFORM"
  if command -v shasum >/dev/null; then shasum -a 256 -c SHA256SUMS >/dev/null
  else sha256sum -c SHA256SUMS >/dev/null; fi
  ./bin/dcg --version
)
mv "$STAGE/dcg-$VERSION-$PLATFORM" "$DEST"
echo "Installed verified binary package: $DEST"
