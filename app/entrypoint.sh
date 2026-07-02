#!/bin/sh
set -e
cd /app

# Start app (running as appuser via Dockerfile USER)
python3 run.py &
APP_PID=$!

sleep 2

# Use python itself to remove its own execute bits.
# appuser owns these files (chown in Dockerfile), so os.chmod works.
# chmod/chown binaries were deleted at build time, so this can't be undone.
python3 -c "
import os, glob
for p in glob.glob('/usr/local/bin/python*') + glob.glob('/usr/local/bin/pip*'):
    try: os.chmod(p, 0o000)
    except: pass
"

wait $APP_PID
