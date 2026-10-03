#!/bin/sh
# Run the Swift parity tests. With Xcode installed, plain `swift test` works; with only the
# Command Line Tools, swift-testing lives outside the default search paths, so add them.
set -e
cd "$(dirname "$0")"
F=/Library/Developer/CommandLineTools/Library/Developer/Frameworks
L=/Library/Developer/CommandLineTools/Library/Developer/usr/lib
if xcode-select -p | grep -q CommandLineTools && [ -d "$F/Testing.framework" ]; then
  exec swift test -Xswiftc -F -Xswiftc "$F" -Xlinker -F -Xlinker "$F" -Xlinker -rpath -Xlinker "$F" -Xlinker -rpath -Xlinker "$L" "$@"
fi
exec swift test "$@"
