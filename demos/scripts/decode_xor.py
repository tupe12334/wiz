#!/usr/bin/env python3
"""Decode report_data's XOR-encoded checksum with the CORRECT key pair
(the app ships [0x42, 0x0A] - the second byte is wrong, see
app/app/services/reports.py). Reads "sequence,encoded_char" CSV lines on
stdin (e.g. from `psql -t -A -F,`).
Usage: psql ... -c "SELECT sequence, encoded_char FROM report_data ORDER BY sequence" -t -A -F',' | decode_xor.py
"""
import sys

KEYS = [0x42, 0x1F]
rows = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    seq, enc = line.split(",")
    rows.append((int(seq), int(enc)))

print("".join(chr(enc ^ KEYS[(seq - 1) % 2]) for seq, enc in sorted(rows)))
