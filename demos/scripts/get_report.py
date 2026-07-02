#!/usr/bin/env python3
"""Call /api/report as the given session. Prints the error body on
failure instead of raising, so this is safe to run against a
still-broken account (that's the point - see challenge 6).
Usage: get_report.py <session_id>
"""
import sys
import urllib.request
import urllib.error
import json

sid = sys.argv[1]
req = urllib.request.Request(
    "http://app:8080/api/report", headers={"Authorization": f"Bearer {sid}"}
)
try:
    print(json.dumps(json.loads(urllib.request.urlopen(req).read()), indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    print(json.dumps(json.loads(e.read()), indent=2))
