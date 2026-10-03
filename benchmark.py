"""
benchmark.py - Percobaan otomatis.
Menjalankan final_version dengan banyak konfigurasi, tiap konfigurasi diulang
REPEAT kali lalu diambil median. Keluaran di folder hasil/

Pemakaian: python benchmark.py [--repeat 3]
"""
import argparse
import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import banner, list_files
from final_version import run_hybrid, run_processes, run_sequential, run_threads

OUT = "hasil"
WORKERS = [1, 2, 4, 8]          # variasi jumlah thread / process
FILE_VARIASI = [4, 8, 12]       # variasi jumlah file (Percobaan 3)
FIXED = 4                       # jumlah worker tetap pada Percobaan 3
HYBRID = [(2, 2), (2, 4), (4, 2), (4, 4)]   # (jumlah proses, thread per proses)


def median_time(fn, files, n, repeat):
    ts, res = [], None
    for _ in range(repeat):
        res, t = fn(files, n) if n else fn(files)
        ts.append(t)
    return statistics.median(ts), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    banner("BENCHMARK PARALLEL LOG FILE ANALYZER")
    semua = list_files()
    rows = []

    def tambah(eks, konf, nfile, thr, prc, waktu, base, lines):
        sp = base / waktu
        w = thr * prc if (thr and prc) else (thr or prc or 1)
        rows.append({"eksperimen": eks, "konfigurasi": konf, "jumlah_file": nfile,
                     "thread": thr, "process": prc, "waktu_detik": round(waktu, 3),
                     "speedup": round(sp, 3), "efisiensi_persen": round(sp / w * 100, 1),
                     "throughput_baris_per_detik": round(lines / waktu)})

    # ---- Percobaan 1 & 2: variasi thread dan process (semua file) ----
    t_seq, ref = median_time(run_sequential, semua, None, a.repeat)
    lines = ref["lines"]
    print(f"Sequential ({len(semua)} file): {t_seq:.2f} dtk")
    tambah("Baseline", "Sequential", len(semua), 0, 0, t_seq, t_seq, lines)
    for n in WORKERS:
        t, r = median_time(run_threads, semua, n, a.repeat)
        assert r == ref, "hasil thread tidak sama dengan sequential!"
        tambah("P1-Thread", f"Thread-{n}", len(semua), n, 0, t, t_seq, lines)
        print(f"  Thread  x{n}: {t:.2f} dtk")
    for n in WORKERS:
        t, r = median_time(run_processes, semua, n, a.repeat)
        assert r == ref, "hasil process tidak sama dengan sequential!"
        tambah("P2-Process", f"Process-{n}", len(semua), 0, n, t, t_seq, lines)
        print(f"  Process x{n}: {t:.2f} dtk")

    # ---- Percobaan 4: HYBRID (proses x thread) ----
    for p, th in HYBRID:
        t, r = median_time(lambda fl, n: run_hybrid(fl, n[0], n[1]), semua, (p, th), a.repeat)
        assert r == ref, "hasil hybrid tidak sama dengan sequential!"
        tambah("P4-Hybrid", f"Hybrid-{p}Px{th}T", len(semua), th, p, t, t_seq, lines)
        print(f"  Hybrid {p}P x {th}T: {t:.2f} dtk")

    # ---- Percobaan 3: variasi jumlah file (worker tetap) ----
    for k in FILE_VARIASI:
        sub = semua[:k]
        ts, r0 = median_time(run_sequential, sub, None, a.repeat)
        tt, r1 = median_time(run_threads, sub, FIXED, a.repeat)
        tp, r2 = median_time(run_processes, sub, FIXED, a.repeat)
        assert r0 == r1 == r2
        tambah("P3-Data", f"Sequential-{k}file", k, 0, 0, ts, ts, r0["lines"])
        tambah("P3-Data", f"Thread-{FIXED}-{k}file", k, FIXED, 0, tt, ts, r0["lines"])
        tambah("P3-Data", f"Process-{FIXED}-{k}file", k, 0, FIXED, tp, ts, r0["lines"])
        print(f"  {k:>2} file: seq {ts:.2f} | thread {tt:.2f} | process {tp:.2f}")

    # ---- Simpan CSV ----
    with open(os.path.join(OUT, "hasil_percobaan.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- Tabel di terminal ----
    print("=" * 60)
    print(f"{'Eksperimen':<11}{'Konfigurasi':<22}{'File':>5}{'Waktu(s)':>10}{'Speedup':>9}{'Efisiensi':>11}")
    for r in rows:
        print(f"{r['eksperimen']:<11}{r['konfigurasi']:<22}{r['jumlah_file']:>5}"
              f"{r['waktu_detik']:>10.2f}{r['speedup']:>8.2f}x{r['efisiensi_persen']:>10.1f}%")

    # ---- Grafik ----
    p1 = [r for r in rows if r["eksperimen"] == "P1-Thread"]
    p2 = [r for r in rows if r["eksperimen"] == "P2-Process"]

    def grafik_waktu(data, kunci, judul, berkas, warna):
        plt.figure(figsize=(6.5, 4))
        plt.plot([r[kunci] for r in data], [r["waktu_detik"] for r in data], "o-", color=warna, label=judul)
        plt.axhline(t_seq, color="gray", linestyle="--", label=f"Sequential ({t_seq:.2f} dtk)")
        for r in data:
            plt.annotate(f"{r['waktu_detik']:.2f}", (r[kunci], r["waktu_detik"]),
                         textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
        plt.xlabel(f"Jumlah {kunci}"); plt.ylabel("Waktu eksekusi (detik)")
        plt.title(f"Waktu vs Jumlah {kunci.capitalize()}")
        plt.xticks([r[kunci] for r in data]); plt.grid(alpha=.3); plt.legend()
        plt.tight_layout(); plt.savefig(os.path.join(OUT, berkas), dpi=150); plt.close()

    grafik_waktu(p1, "thread", "Multithread", "grafik_waktu_vs_thread.png", "tab:blue")
    grafik_waktu(p2, "process", "Multiprocessing", "grafik_waktu_vs_process.png", "tab:green")

    # Speedup vs konfigurasi
    p4 = [r for r in rows if r["eksperimen"] == "P4-Hybrid"]
    sel = p1 + p2 + p4
    plt.figure(figsize=(11, 4.5))
    peta = {"P1-Thread": "tab:blue", "P2-Process": "tab:green", "P4-Hybrid": "tab:orange"}
    warna = [peta[r["eksperimen"]] for r in sel]
    plt.bar([r["konfigurasi"] for r in sel], [r["speedup"] for r in sel], color=warna)
    for i, r in enumerate(sel):
        plt.text(i, r["speedup"] + 0.02, f"{r['speedup']:.2f}x", ha="center", fontsize=8)
    plt.axhline(1.0, color="red", linestyle="--", label="Sequential (1x)")
    plt.ylabel("Speedup (T_sequential / T)"); plt.xlabel("Konfigurasi")
    plt.title("Speedup vs Konfigurasi (biru = thread, hijau = process, oranye = hybrid)")
    plt.xticks(rotation=30); plt.legend(); plt.grid(axis="y", alpha=.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "grafik_speedup_vs_konfigurasi.png"), dpi=150); plt.close()

    # Waktu vs jumlah file (pelengkap Percobaan 3)
    p3 = [r for r in rows if r["eksperimen"] == "P3-Data"]
    plt.figure(figsize=(6.5, 4))
    for awal, label in (("Sequential", "Sequential"), ("Thread", f"Thread-{FIXED}"), ("Process", f"Process-{FIXED}")):
        d = [r for r in p3 if r["konfigurasi"].startswith(awal)]
        plt.plot([r["jumlah_file"] for r in d], [r["waktu_detik"] for r in d], "o-", label=label)
    plt.xlabel("Jumlah file"); plt.ylabel("Waktu eksekusi (detik)")
    plt.title("Waktu vs Jumlah File"); plt.xticks(FILE_VARIASI); plt.grid(alpha=.3); plt.legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "grafik_waktu_vs_jumlah_file.png"), dpi=150); plt.close()

    print("=" * 60)
    print(f"Tabel & grafik tersimpan di folder '{OUT}/'")
    print("=" * 60)


if __name__ == "__main__":
    main()
