# OpenMP Laboratory Project - Mardan Ibragimov (230103054)

C++17/OpenMP implementation and benchmark results for Labs 1-5 and the Lab 6 bonus challenge from the Shared-Memory Concurrency & OpenMP Paradigms laboratory manual.

## Student
- **Name:** Mardan Ibragimov
- **Student ID:** 230103054
- **Course:** Parallel Programming
- **Environment:** Windows 11 Pro, Intel Core i7-12700H (14 cores / 20 logical processors)
- **Compiler used in the submitted runs:** GCC 13.2.0 (MSYS2), C++17, OpenMP via `-fopenmp`

## Repository structure
```text
openmp_230103054_final/
├── README.md
├── .gitignore
├── lab1/                # Fork-join, non-determinism, oversubscription
├── lab2/                # Pi race / critical / reduction scaling
├── lab3/                # Mandelbrot scheduling: static/dynamic/guided
├── lab4/                # False sharing / padding / thread-local
├── lab5/                # Recursive OpenMP task merge sort
├── lab6_bonus/          # 3-stage bounded-queue pipeline
├── report/              # Final PDF/DOCX report + generated figures
└── screenshots/         # Terminal evidence from executed runs
```

## Compile and run
Open a terminal in each lab folder and use:

```powershell
g++ -O2 -std=c++17 -fopenmp lab1.cpp -o lab1.exe
.\lab1.exe
```

Replace `lab1` with the corresponding lab number. For the bonus folder:

```powershell
g++ -O2 -std=c++17 -fopenmp lab6_bonus.cpp -o lab6_bonus.exe
.\lab6_bonus.exe
```

## Raw benchmark outputs
The committed CSV/TXT files are the actual outputs used in the final report:
- `lab1/lab1_nondeterminism.txt`
- `lab1/lab1_oversubscription.csv`
- `lab2/lab2_race.csv`
- `lab2/lab2_critical.csv`
- `lab2/lab2_scaling.csv`
- `lab3/lab3_benchmark.csv`
- `lab3/lab3_thread_work.csv`
- `lab4/lab4_false_sharing.csv`
- `lab5/lab5_cutoff_sweep.csv`
- `lab5/lab5_work_span.csv`
- `lab6_bonus/lab6_pipeline.csv`

## Final report
- `report/OpenMP_Lab_Report_230103054.pdf`
- `report/OpenMP_Lab_Report_230103054.docx`

The report contains methodology, hardware information, all measured tables, plots, analytical answers for Labs 1-5, bonus pipeline discussion, conclusions, and terminal screenshots.

## Key measured results
- Lab 2 reduction: **7.21x speedup at 16 threads**.
- Lab 4 padding: **2.85x faster than unpadded at 16 threads**.
- Lab 5 task cutoff: **K=1 = 9.564 s**, practical region around **0.10 s**.
- Lab 6: throughput decreased from **1121.5 to 401.3 packets/s** as Stage 2 workload increased.

## Note
Windows-specific runs do not include Linux `perf stat` hardware counters. The report states this explicitly and uses the measured timing/scaling evidence for the false-sharing analysis.
