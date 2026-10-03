"""
FINAL CODE (semua bug sudah diperbaiki)
Parallel Log File Analyzer: Sequential vs Multithread vs Multiprocessing.

Perbaikan:
  BUG-1 Race condition   -> TIDAK ada state global bersama. Tiap tugas membuat
                            hasil lokal, penggabungan (reduce) hanya dilakukan
                            thread/proses utama (tanpa Lock, tanpa kontensi).
  BUG-2 Load imbalance   -> Dynamic scheduling: file diurutkan dari terbesar,
                            lalu worker mengambil 1 file setiap selesai
                            (ThreadPoolExecutor.map / Pool.imap_unordered, chunksize=1).
  BUG-3 Memori terpisah  -> Proses mengembalikan hasil lewat return value
                            (di-pickle ke proses induk), bukan lewat variabel global.

Pemakaian: python final_version.py [--threads 4] [--procs 4] [--files N] [--quiet]
"""
import argparse
import multiprocessing
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

from common import analyze_file, banner, list_files, merge_result, new_result

_print_lock = threading.Lock()   # merapikan output antar thread


def _nama_worker():
    p = multiprocessing.current_process().name
    t = threading.current_thread().name
    if p == "MainProcess":
        return t
    return p if t == "MainThread" else f"{p}/{t}"     # hybrid: proses/thread


def _task(arg):
    path, verbose = arg
    nama, base = _nama_worker(), os.path.basename(path)
    if verbose:
        with _print_lock:
            print(f"[MULAI]   {nama:<28} {base}\n", end="", flush=True)
    t0 = time.perf_counter()
    res = analyze_file(path)                   # hasil LOKAL
    if verbose:
        with _print_lock:
            print(f"[SELESAI] {nama:<28} {base}  ({res['lines']} baris, "
                  f"{time.perf_counter() - t0:.2f} dtk)\n", end="", flush=True)
    return res


def _tasks(files, verbose):
    urut = sorted(files, key=os.path.getsize, reverse=True)   # terbesar dulu
    return [(f, verbose) for f in urut]


def run_sequential(files, verbose=False):
    t0 = time.perf_counter()
    total = new_result()
    for r in map(_task, _tasks(files, verbose)):
        merge_result(total, r)
    return total, time.perf_counter() - t0


def run_threads(files, n, verbose=False):
    t0 = time.perf_counter()
    total = new_result()
    with ThreadPoolExecutor(max_workers=n, thread_name_prefix="Thread") as ex:
        for r in ex.map(_task, _tasks(files, verbose)):
            merge_result(total, r)             # reduce hanya di thread utama
    return total, time.perf_counter() - t0


def run_processes(files, n, verbose=False):
    t0 = time.perf_counter()
    total = new_result()
    with Pool(processes=n) as pool:
        for r in pool.imap_unordered(_task, _tasks(files, verbose), chunksize=1):
            merge_result(total, r)
    return total, time.perf_counter() - t0


def _bagi_lpt(files, k):
    """Bagi file ke k kelompok seimbang (terbesar dulu ke kelompok teringan)."""
    kelompok, beban = [[] for _ in range(k)], [0] * k
    for f in sorted(files, key=os.path.getsize, reverse=True):
        i = beban.index(min(beban))
        kelompok[i].append(f)
        beban[i] += os.path.getsize(f)
    return [g for g in kelompok if g]


def _hybrid_batch(arg):
    """Dijalankan di dalam 1 proses: kelompok file diproses oleh beberapa thread."""
    paths, n_threads, verbose = arg
    total = new_result()
    with ThreadPoolExecutor(max_workers=n_threads, thread_name_prefix="T") as ex:
        for r in ex.map(_task, [(p, verbose) for p in paths]):
            merge_result(total, r)
    return total


def run_hybrid(files, n_proc, n_thread, verbose=False):
    """HYBRID: n_proc proses, masing-masing menjalankan n_thread thread."""
    t0 = time.perf_counter()
    total = new_result()
    jobs = [(g, n_thread, verbose) for g in _bagi_lpt(files, n_proc)]
    with Pool(processes=n_proc) as pool:
        for r in pool.imap_unordered(_hybrid_batch, jobs):
            merge_result(total, r)
    return total, time.perf_counter() - t0


def tampilkan_hasil(res):
    print("HASIL ANALISIS LOG")
    print(f"  Total baris       : {res['lines']}  (rusak: {res['bad']})")
    print(f"  Total byte terkirim: {res['bytes']:,}")
    print(f"  Level             : {dict(res['levels'])}")
    print(f"  Status code teratas: {res['status'].most_common(5)}")
    print(f"  IP teratas        : {res['ips'].most_common(3)}")
    print(f"  User teraktif     : {res['users'].most_common(3)}")
    jam, n = res['hours'].most_common(1)[0]
    print(f"  Jam tersibuk      : {jam:02d}:00 ({n} request)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--hproc", type=int, default=4, help="jumlah proses pada mode hybrid")
    ap.add_argument("--hthread", type=int, default=2, help="thread per proses pada mode hybrid")
    ap.add_argument("--files", type=int, default=None, help="jumlah file yang dipakai")
    ap.add_argument("--quiet", action="store_true", help="sembunyikan log per file")
    a = ap.parse_args()
    verbose = not a.quiet

    banner("PARALLEL LOG FILE ANALYZER (FINAL)")
    files = list_files(a.files)
    mb = sum(os.path.getsize(f) for f in files) / 1e6
    print(f"CPU core terdeteksi : {os.cpu_count()}")
    print(f"Jumlah file         : {len(files)} ({mb:.1f} MB)")
    print(f"Jumlah thread       : {a.threads}")
    print(f"Jumlah process      : {a.procs}")
    print(f"Hybrid              : {a.hproc} proses x {a.hthread} thread = {a.hproc * a.hthread} worker")

    print("=" * 60 + "\nSEQUENTIAL (1 worker)\n" + "=" * 60)
    ref, t_seq = run_sequential(files, verbose)
    print(f"Selesai: {t_seq:.2f} detik")

    print("=" * 60 + f"\nMULTITHREAD ({a.threads} thread)\n" + "=" * 60)
    r_thr, t_thr = run_threads(files, a.threads, verbose)
    print(f"Selesai: {t_thr:.2f} detik")

    print("=" * 60 + f"\nMULTIPROCESSING ({a.procs} proses)\n" + "=" * 60)
    r_proc, t_proc = run_processes(files, a.procs, verbose)
    print(f"Selesai: {t_proc:.2f} detik")

    print("=" * 60 + f"\nHYBRID ({a.hproc} proses x {a.hthread} thread)\n" + "=" * 60)
    r_hyb, t_hyb = run_hybrid(files, a.hproc, a.hthread, verbose)
    print(f"Selesai: {t_hyb:.2f} detik")

    print("=" * 60)
    tampilkan_hasil(ref)
    print("=" * 60)
    print("RINGKASAN")
    print(f"{'Pendekatan':<16}{'Worker':>7}{'Waktu(s)':>10}{'Speedup':>9}"
          f"{'Efisiensi':>11}{'Throughput(baris/s)':>21}{'Valid':>7}")
    for nama, w, t, r in (("Sequential", 1, t_seq, ref),
                          ("Multithread", a.threads, t_thr, r_thr),
                          ("Multiprocessing", a.procs, t_proc, r_proc),
                          (f"Hybrid {a.hproc}Px{a.hthread}T", a.hproc * a.hthread, t_hyb, r_hyb)):
        sp = t_seq / t
        print(f"{nama:<16}{w:>7}{t:>10.2f}{sp:>8.2f}x{sp / w * 100:>10.1f}%"
              f"{r['lines'] / t:>21,.0f}{'OK' if r == ref else 'BEDA':>7}")
    print("=" * 60)
    print(f"Waktu total : {t_seq + t_thr + t_proc + t_hyb:.2f} detik (semua pendekatan)")
    print("=" * 60)


if __name__ == "__main__":
    main()
