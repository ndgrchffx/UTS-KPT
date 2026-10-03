"""
generate_logs.py - Membuat dataset log server sintetis.
Ukuran file sengaja TIDAK seragam (0.4x s.d. 2.0x BASE_LINES) supaya masalah
load imbalance dapat diamati.

Pemakaian: python generate_logs.py [--files N] [--lines N]
"""
import argparse
import os
import random

from common import BASE_LINES, LOG_DIR, NUM_FILES, SEED, banner

PATHS = ["/", "/login", "/logout", "/api/products", "/api/orders", "/api/users",
         "/cart", "/checkout", "/search", "/static/app.js", "/static/style.css",
         "/admin", "/profile", "/api/payments", "/help"]
METHODS = ["GET"] * 7 + ["POST"] * 3 + ["PUT", "DELETE"]
STATUS = [200, 201, 301, 304, 400, 401, 403, 404, 500, 502, 503]
STATUS_W = [62, 5, 4, 6, 4, 3, 2, 8, 3, 1.5, 1.5]
HOUR_W = [1, 1, 1, 1, 1, 2, 3, 5, 8, 10, 10, 9, 8, 9, 10, 10, 9, 8, 7, 7, 6, 4, 3, 2]


def level_of(status):
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARNING"
    return "INFO"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", type=int, default=NUM_FILES)
    ap.add_argument("--lines", type=int, default=BASE_LINES)
    a = ap.parse_args()

    rng = random.Random(SEED)
    ips = [f"{rng.choice([10, 103, 114, 180, 203])}.{rng.randint(0, 255)}."
           f"{rng.randint(0, 255)}.{rng.randint(1, 254)}" for _ in range(400)]
    users = [f"user{i:03d}" for i in range(1, 201)]

    os.makedirs(LOG_DIR, exist_ok=True)
    banner("GENERATOR DATASET LOG SERVER")
    total = 0
    for i in range(a.files):
        faktor = 0.4 + 1.6 * i / max(1, a.files - 1)   # 0.4x ... 2.0x
        n = int(a.lines * faktor)
        out = []
        for _ in range(n):
            if rng.random() < 0.005:                    # 0,5% baris rusak (malformed)
                out.append("### baris log rusak / corrupt ###")
                continue
            st = rng.choices(STATUS, STATUS_W)[0]
            jam = rng.choices(range(24), HOUR_W)[0]
            out.append(
                f'{rng.choice(ips)} - {rng.choice(users)} '
                f'[2026-10-02 {jam:02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}] '
                f'"{rng.choice(METHODS)} {rng.choice(PATHS)} HTTP/1.1" '
                f'{st} {rng.randint(200, 90000)} {level_of(st)}')
        name = os.path.join(LOG_DIR, f"access_log_{i + 1:02d}.log")
        with open(name, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
        total += n
        print(f"[OK] {name}  {n:>7} baris")
    print("=" * 60)
    print(f"Total {a.files} file, {total} baris")
    print("=" * 60)


if __name__ == "__main__":
    main()
