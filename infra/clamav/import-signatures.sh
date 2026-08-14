#!/bin/sh
set -eu

test -d /import
test -f /import/SHA256SUMS || {
  echo "Offline bundle is missing SHA256SUMS." >&2
  exit 78
}
test -f /import/APPROVED-OFFLINE-BUNDLE || {
  echo "Offline bundle is missing its approval marker." >&2
  exit 78
}

cd /import
sha256sum -c SHA256SUMS

found=0
for source in ./*.cvd ./*.cld; do
  test -f "$source" || continue
  test ! -L "$source" || { echo "Symlinked signatures are forbidden." >&2; exit 78; }
  case "$(basename "$source")" in
    main.cvd|main.cld|daily.cvd|daily.cld|bytecode.cvd|bytecode.cld) ;;
    *) echo "Unexpected signature filename: $source" >&2; exit 78 ;;
  esac
  sigtool --info "$source" >/dev/null
  found=$((found + 1))
done
test "$found" -gt 0 || { echo "No validated ClamAV signature database found." >&2; exit 78; }

staging=/var/lib/clamav/.offline-import
mkdir -p "$staging"
find "$staging" -mindepth 1 -maxdepth 1 -type f -delete
for source in ./*.cvd ./*.cld; do
  test -f "$source" || continue
  cp "$source" "$staging/$(basename "$source")"
done

# The service is stopped by the PowerShell wrapper. Remove only the six known
# database filenames after every staged replacement has passed sigtool.
find /var/lib/clamav -maxdepth 1 -type f \
  \( -name 'main.cvd' -o -name 'main.cld' \
     -o -name 'daily.cvd' -o -name 'daily.cld' \
     -o -name 'bytecode.cvd' -o -name 'bytecode.cld' \) -delete

for staged in "$staging"/*.cvd "$staging"/*.cld; do
  test -f "$staged" || continue
  mv "$staged" "/var/lib/clamav/$(basename "$staged")"
done
rmdir "$staging"
sha256sum SHA256SUMS | awk '{print $1}' > /var/lib/clamav/offline-import.receipt
echo "Approved offline ClamAV signatures imported."
