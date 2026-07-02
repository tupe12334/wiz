#!/usr/bin/env python3
"""Log in directly against the app Service, bypassing nginx's DLP filter.
Usage: login.py <username> <password>
"""
import sys
import urllib.request
import json

username, password = sys.argv[1], sys.argv[2]
data = json.dumps({"username": username, "password": password}).encode()
req = urllib.request.Request(
    "http://app:8080/api/login", data=data, headers={"Content-Type": "application/json"}
)
resp = json.loads(urllib.request.urlopen(req).read())
print(resp["session_id"])
