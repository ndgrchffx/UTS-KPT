"""
bug_version.py - CODE WITH BUG
Parallel Log File Analyzer (versi SENGAJA bermasalah).

Bug yang sengaja dimasukkan:
  BUG-1  RACE CONDITION (multithread)
         Banyak thread memperbarui dict global `shared` tanpa Lock
         (pola read -> modify -> write). Update thread lain tertimpa,
         sehingga total baris / error yang dihitung KURANG dari yang benar.
         (time.sleep(0) hanya memperbesar peluang pergantian thread agar bug
          tampak jelas dan konsisten saat didemokan.)
  BUG-2  LOAD IMBALANCE (multithread & multiprocessing)
         File dibagi statis berurutan (contiguous). Karena ukuran file naik
         dari kecil ke besar, worker terakhir menerima file terberat sementara
         worker lain sudah idle.
  BUG-3  MEMORI TIDAK DIBAGI ANTAR PROSES (multiprocessing)
         Setiap proses punya salinan `shared` sendiri, sehingga proses induk
         tetap membaca 0 -> hasil hilang.

Pemakaian: python bug_version.py [--workers 4]
"""
import argparse
import math
import multiprocessing
import threading
import sys
import time
from multiprocessing import Pool

from common import analyze_file, banner, list_files, merge_result, new_result

shared = {"lines": 0, "errors": 0}      # variabel global yang dipakai bersama
print_lock = threading.Lock()           # hanya merapikan output (BUKAN melindungi counter)


def unsafe_add(key):
    tmp = shared[key]          # READ
    time.sleep(0)              # titik pergantian konteks (thread lain bisa menulis)
    shared[key] = tmp + 1      # WRITE  -> menimpa update thread lain (RACE CONDITION)


def tally(level):
    unsafe_add("lines")
    if level == "ERROR":
        unsafe_add("errors")


def static_chunks(files, n):
    """Pembagian statis berurutan -> penyebab LOAD IMBALANCE."""
    size = math.ceil(len(files) / n)
    return [files[i * size:(i + 1) * size] for i in range(n) if files[i * size:(i + 1) * size]]


def run_chunk(chunk):
    nama = multiprocessing.current_process().name
    if nama == "MainProcess":
        nama = threading.current_thread().name
    t0 = time.perf_counter()
    with print_lock:
        print(f"{nama} mulai bekerja ({len(chunk)} file)\n", end="", flush=True)
    for path in chunk:
        analyze_file(path, on_line=tally)
    dur = time.perf_counter() - t0
    with print_lock:
        print(f"{nama} selesai dalam {dur:.2f} detik\n", end="", flush=True)
    return nama, dur


def laporan_imbalance(durasi):
    rata = sum(durasi) / len(durasi)
    print(f"Waktu per worker : {[round(d, 2) for d in durasi]}")
    print(f"Terlama / rata-rata = {max(durasi) / rata:.2f}x  (ideal = 1.00x -> LOAD IMBALANCE)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    banner("PARALLEL LOG FILE ANALYZER - VERSI BUG")
    files = list_files()

    # ---- Referensi: hasil benar (sequential) ----
    benar = new_result()
    for f in files:
        merge_result(benar, analyze_file(f))
    valid = benar["lines"] - benar["bad"]
    err = benar["levels"]["ERROR"]
    print(f"[REFERENSI SEQUENTIAL] baris valid = {valid}, ERROR = {err}\n")

    # ---- BUG-1 & BUG-2: multithread ----
    print("-" * 60)
    print(f"MULTITHREAD ({a.workers} thread) - global dict tanpa Lock")
    print("-" * 60)
    shared["lines"] = shared["errors"] = 0
    hasil = []
    chunks = static_chunks(files, a.workers)
    threads = [threading.Thread(target=lambda c=c: hasil.append(run_chunk(c)),
                                name=f"Thread-{i + 1}") for i, c in enumerate(chunks)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    waktu = time.perf_counter() - t0
    print(f"Baris valid terhitung : {shared['lines']:>8} (seharusnya {valid})")
    print(f"ERROR terhitung       : {shared['errors']:>8} (seharusnya {err})")
    print(f"Update HILANG         : {valid - shared['lines']:>8}  <-- RACE CONDITION")
    laporan_imbalance([d for _, d in hasil])
    print(f"Waktu total           : {waktu:.2f} detik\n")

    # ---- BUG-3 & BUG-2: multiprocessing ----
    print("-" * 60)
    print(f"MULTIPROCESSING ({a.workers} proses) - variabel global tidak dibagi")
    print("-" * 60)
    shared["lines"] = shared["errors"] = 0
    t0 = time.perf_counter()
    with Pool(a.workers) as pool:
        hasil = pool.map(run_chunk, static_chunks(files, a.workers))
    waktu = time.perf_counter() - t0
    print(f"Baris valid terhitung di proses induk : {shared['lines']} (seharusnya {valid})  <-- HASIL HILANG")
    laporan_imbalance([d for _, d in hasil])
    print(f"Waktu total           : {waktu:.2f} detik")
    print("=" * 60)


if __name__ == "__main__":
    main()
