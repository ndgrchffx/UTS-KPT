"""
common.py - Konfigurasi dan fungsi inti yang dipakai semua program.

"""
import glob
import os
import re
import sys
from collections import Counter
from datetime import datetime

NAMA = "Naila Salsabila"
NPM = "247006111004"

# ---- Parameter dataset  ----
SEED = 2026
NUM_FILES = 12
BASE_LINES = 20000
LOG_DIR = "logs"

# Format log:
# 203.0.113.5 - user12 [2026-10-02 10:15:32] "GET /api/products HTTP/1.1" 200 5123 INFO
LOG_RE = re.compile(
    r'^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}) - (?P<user>\S+) \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) HTTP/\d\.\d" '
    r'(?P<status>\d{3}) (?P<bytes>\d+) (?P<level>INFO|WARNING|ERROR)$'
)
TS_FORMAT = "%Y-%m-%d %H:%M:%S"

def banner(judul):
    garis = "=" * 60
    print(garis)
    print(judul)
    print(f"By {NAMA} ({NPM})")
    print(garis)

def new_result():
    return {
        "lines": 0, "bad": 0, "bytes": 0,
        "levels": Counter(), "status": Counter(),
        "ips": Counter(), "users": Counter(), "hours": Counter(),
    }

def merge_result(total, part):
    """Gabungkan hasil parsial `part` ke `total` (tahap reduce)."""
    for k in ("lines", "bad", "bytes"):
        total[k] += part[k]
    for k in ("levels", "status", "ips", "users", "hours"):
        total[k].update(part[k])
    return total

def analyze_file(path, on_line=None):
    """
    Analisis satu file log (tugas CPU-bound: regex + parsing waktu).

    """
    res = new_result()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            res["lines"] += 1
            m = LOG_RE.match(line.rstrip("\n"))
            if m is None:
                res["bad"] += 1
                continue
            level = m["level"]
            res["bytes"] += int(m["bytes"])
            res["levels"][level] += 1
            res["status"][m["status"]] += 1
            res["ips"][m["ip"]] += 1
            res["users"][m["user"]] += 1
            res["hours"][datetime.strptime(m["ts"], TS_FORMAT).hour] += 1
    return res