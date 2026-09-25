#include <omp.h>
#include <algorithm>
#include <cassert>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <vector>

void merge_ranges(std::vector<int>& a, std::vector<int>& temp, int left, int mid, int right) {
    int i = left, j = mid, k = left;
    while (i < mid && j < right) {
        temp[k++] = (a[i] <= a[j]) ? a[i++] : a[j++];
    }
    while (i < mid) temp[k++] = a[i++];
    while (j < right) temp[k++] = a[j++];
    for (int x = left; x < right; ++x) a[x] = temp[x];
}

void parallel_merge_sort_rec(std::vector<int>& a, std::vector<int>& temp,
                             int left, int right, int cutoff) {
    int n = right - left;
    if (n <= 1) return;
    if (n <= cutoff) {
        std::sort(a.begin() + left, a.begin() + right);
        return;
    }
    int mid = left + n / 2;

    #pragma omp task shared(a, temp) firstprivate(left, mid, cutoff)
    parallel_merge_sort_rec(a, temp, left, mid, cutoff);

    #pragma omp task shared(a, temp) firstprivate(mid, right, cutoff)
    parallel_merge_sort_rec(a, temp, mid, right, cutoff);

    #pragma omp taskwait
    merge_ranges(a, temp, left, mid, right);
}

double run_sort(const std::vector<int>& input, int cutoff, int threads, bool verify) {
    std::vector<int> a = input;
    std::vector<int> temp(a.size());
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        #pragma omp single
        parallel_merge_sort_rec(a, temp, 0, static_cast<int>(a.size()), cutoff);
    }
    double elapsed = omp_get_wtime() - t0;
    if (verify) assert(std::is_sorted(a.begin(), a.end()));
    return elapsed;
}

int main() {
    omp_set_dynamic(0);
    const int N = 5'000'000;
    int threads = std::max(1, omp_get_num_procs());
    std::cout << "LAB 5 — Recursive Task-Based Parallelism (Merge Sort)\n";
    std::cout << "N=" << N << ", threads=" << threads << "\n";

    std::mt19937 rng(230103054u);
    std::uniform_int_distribution<int> dist(0, 10'000'000);
    std::vector<int> data(N);
    for (int& x : data) x = dist(rng);

    // Task 5.1 verification
    double verify_time = run_sort(data, 50'000, threads, true);
    std::cout << "Task 5.1 verification PASSED | cutoff=50000 | time="
              << std::fixed << std::setprecision(4) << verify_time << " s\n\n";

    // Task 5.2 cutoff sweep from the manual.
    std::vector<int> K = {1, 10, 100, 1000, 10000, 50000, 100000};
    std::ofstream csv("lab5_cutoff_sweep.csv");
    csv << "cutoff,time_seconds\n";
    std::cout << "Task 5.2 — Cutoff sweep\n";
    for (int cutoff : K) {
        double t = run_sort(data, cutoff, threads, true);
        csv << cutoff << ',' << t << '\n';
        std::cout << "K=" << std::setw(6) << cutoff << " | time="
                  << std::fixed << std::setprecision(4) << t << " s\n";
    }

    // Task 5.3 empirical Work/Span-style measurements.
    // T1: same algorithm with one OpenMP thread.
    // T_infinity cannot be measured literally on finite hardware; we report an empirical proxy
    // using the maximum available team and leave the theoretical derivation for the report.
    const int best_cutoff = 50'000;
    double T1 = run_sort(data, best_cutoff, 1, true);
    double Tp = run_sort(data, best_cutoff, threads, true);
    double empirical_parallelism = T1 / Tp;
    std::ofstream ws("lab5_work_span.csv");
    ws << "T1_seconds,Tp_seconds,threads,empirical_parallelism\n";
    ws << T1 << ',' << Tp << ',' << threads << ',' << empirical_parallelism << '\n';

    std::cout << "\nTask 5.3 empirical measurements\n";
    std::cout << "T1 (1 thread) = " << T1 << " s\n";
    std::cout << "T(P) (" << threads << " threads) = " << Tp << " s\n";
    std::cout << "Measured T1/T(P) = " << empirical_parallelism << "\n";
    std::cout << "Generated: lab5_cutoff_sweep.csv, lab5_work_span.csv\n";
    return 0;
}
