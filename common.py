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