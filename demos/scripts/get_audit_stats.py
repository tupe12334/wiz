#!/usr/bin/env python3
"""Call /api/audit/statistics as the given (admin) session.
Usage: get_audit_stats.py <session_id>
"""
import sys
import urllib.request
import json

sid = sys.argv[1]
req = urllib.request.Request(
    "http://app:8080/api/audit/statistics", headers={"Authorization": f"Bearer {sid}"}
)
print(json.dumps(json.loads(urllib.request.urlopen(req).read()), indent=2)[:400])
