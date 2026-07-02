#!/usr/bin/env python3
"""Provision an employee account (admin session required), then log in
as that new account. Prints "<session_id> <user_id>" on one line for
easy `read sid uid <<< "$(...)"` capture in a shell script/demo.
Usage: provision_and_login.py <admin_session_id> <username> <full_name> <email>
"""
import sys
import urllib.request
import json

admin_sid, username, full_name, email = sys.argv[1:5]

req = urllib.request.Request(
    "http://app:8080/api/captcha/verify",
    data=b"{}",
    headers={"Authorization": f"Bearer {admin_sid}", "Content-Type": "application/json"},
    method="POST",
)
token = json.loads(urllib.request.urlopen(req).read())["token"]

body = json.dumps({"username": username, "full_name": full_name, "email": email}).encode()
req2 = urllib.request.Request(
    "http://app:8080/api/admin/create-account",
    data=body,
    headers={
        "Authorization": f"Bearer {admin_sid}",
        "X-Captcha-Token": token,
        "Content-Type": "application/json",
    },
    method="POST",
)
account = json.loads(urllib.request.urlopen(req2).read())["account"]

login_body = json.dumps({"username": username, "password": account["password"]}).encode()
req3 = urllib.request.Request(
    "http://app:8080/api/login", data=login_body, headers={"Content-Type": "application/json"}
)
new_sid = json.loads(urllib.request.urlopen(req3).read())["session_id"]

print(f"{new_sid} {account['user_id']}")
