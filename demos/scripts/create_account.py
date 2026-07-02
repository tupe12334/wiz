#!/usr/bin/env python3
"""Provision an employee account through the admin API.
Usage: create_account.py <session_id> <username> <full_name> <email>
"""
import sys
import urllib.request
import json

sid, username, full_name, email = sys.argv[1:5]

req = urllib.request.Request(
    "http://app:8080/api/captcha/verify",
    data=b"{}",
    headers={"Authorization": f"Bearer {sid}", "Content-Type": "application/json"},
    method="POST",
)
token = json.loads(urllib.request.urlopen(req).read())["token"]

body = json.dumps({"username": username, "full_name": full_name, "email": email}).encode()
req2 = urllib.request.Request(
    "http://app:8080/api/admin/create-account",
    data=body,
    headers={
        "Authorization": f"Bearer {sid}",
        "X-Captcha-Token": token,
        "Content-Type": "application/json",
    },
    method="POST",
)
print(json.dumps(json.loads(urllib.request.urlopen(req2).read()), indent=2))
