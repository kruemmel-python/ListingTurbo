#!/usr/bin/env bash
set -euo pipefail
native_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$native_root/bin"
g++ -std=c++17 -O3 -fPIC -shared "$native_root/src/listingturbo_native.cpp" -ldl -o "$native_root/bin/liblistingturbo_native.so"
echo "ListingTurbo Native Backend gebaut: $native_root/bin/liblistingturbo_native.so"
