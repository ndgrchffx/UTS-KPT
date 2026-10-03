# Parallel Log File Analyzer

UTS Komputasi Paralel dan Terdistribusi - Naila Salsabila (247006111004)

Membutuhkan Python 3.9+ dan `pip install matplotlib` (hanya untuk benchmark.py)

Urutan menjalankan:

1. `python generate_logs.py` -> membuat dataset di folder logs/ (12 file, ~288 ribu baris)
2. `python bug_version.py` -> Code with Bug (race condition, load imbalance, memori tidak dibagi)
3. `python final_version.py` -> Final Code: Sequential, Multithread, Multiprocessing, Hybrid
   (opsi: --threads 4 --procs 4 --hproc 4 --hthread 2 --files 12 --quiet)
4. `python benchmark.py` -> percobaan (thread, process, hybrid, jumlah file) + tabel + grafik di folder hasil/

Parameter dataset: SEED = 2026, NUM_FILES = 12, BASE_LINES = 20000 (ukuran file bertingkat 0,4x sampai 2x).
