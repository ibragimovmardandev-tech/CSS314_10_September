#include <omp.h>
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <vector>

constexpr long long ITERATIONS = 100'000'000LL;

// Volatile prevents the compiler from optimizing away the repeated shared writes.
double unpadded_test(int threads) {
    std::vector<long long> storage(threads, 0);
    volatile long long* counters = storage.data();
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        for (long long i = 0; i < ITERATIONS; ++i) counters[tid]++;
    }
    double t = omp_get_wtime() - t0;
    volatile long long check = std::accumulate(storage.begin(), storage.end(), 0LL);
    (void)check;
    return t;
}

double padded_test(int threads) {
    constexpr int STRIDE = 8; // 8 * 8 bytes = 64 bytes
    std::vector<long long> storage(static_cast<size_t>(threads) * STRIDE, 0);
    volatile long long* counters = storage.data();
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        size_t idx = static_cast<size_t>(tid) * STRIDE;
        for (long long i = 0; i < ITERATIONS; ++i) counters[idx]++;
    }
    double t = omp_get_wtime() - t0;
    volatile long long check = 0;
    for (int tid = 0; tid < threads; ++tid) check += storage[static_cast<size_t>(tid) * STRIDE];
    (void)check;
    return t;
}

double thread_local_test(int threads) {
    std::vector<long long> storage(threads, 0);
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        long long local = 0;
        for (long long i = 0; i < ITERATIONS; ++i) {
            // Keep an actual arithmetic dependency so the loop represents local work.
            local += (i & 1LL);
        }
        storage[tid] = local; // one shared write at the end
    }
    double t = omp_get_wtime() - t0;
    volatile long long check = std::accumulate(storage.begin(), storage.end(), 0LL);
    (void)check;
    return t;
}

int main() {
    omp_set_dynamic(0);
    std::cout << "LAB 4 — Memory Hierarchy, Cache Coherency, and False Sharing\n";
    std::cout << "Iterations per thread: " << ITERATIONS << "\n\n";

    std::vector<int> P = {1, 2, 4, 8, 16};
    std::ofstream csv("lab4_false_sharing.csv");
    csv << "threads,unpadded_seconds,padded_seconds,thread_local_seconds,padding_speedup\n";

    for (int p : P) {
        double a = unpadded_test(p);
        double b = padded_test(p);
        double c = thread_local_test(p);
        double speedup = a / b;
        csv << p << ',' << a << ',' << b << ',' << c << ',' << speedup << '\n';
        std::cout << "P=" << std::setw(2) << p
                  << " | unpadded=" << std::fixed << std::setprecision(4) << a << " s"
                  << " | padded=" << b << " s"
                  << " | local=" << c << " s"
                  << " | unpadded/padded=" << std::setprecision(2) << speedup << "x\n";
    }

    std::cout << "\nTask 4.4 note: the manual's perf command is Linux-specific.\n";
    std::cout << "On Windows, submit Task Manager/CPU evidence unless your instructor requires WSL/Linux perf.\n";
    std::cout << "Generated: lab4_false_sharing.csv\n";
    return 0;
}
