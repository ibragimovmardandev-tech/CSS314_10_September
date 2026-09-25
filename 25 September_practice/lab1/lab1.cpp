#include <omp.h>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

static volatile double sink = 0.0;

void print_team_once(int threads, int run_id) {
    std::cout << "\n--- Run " << run_id << " | team size = " << threads << " ---\n";
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        int team = omp_get_num_threads();
        #pragma omp critical
        {
            std::cout << "Thread " << tid << " of " << team << "\n";
        }
    }
}

double creation_join_time(int threads) {
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        #pragma omp atomic
        sink += tid * 1e-12;
    }
    return omp_get_wtime() - t0;
}

double saturation_test(int threads, long long work_per_thread) {
    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        double local = 0.0;
        for (long long i = 1; i <= work_per_thread; ++i) {
            local += std::sqrt(static_cast<double>(i));
        }
        #pragma omp atomic
        sink += local;
    }
    return omp_get_wtime() - t0;
}

int main() {
    omp_set_dynamic(0);
    const int demo_threads = 4;

    std::ofstream nondet("lab1_nondeterminism.txt");
    std::streambuf* oldbuf = std::cout.rdbuf();

    std::cout << "LAB 1 — Fork-Join Model, Team Creation, and Thread Scoping\n";
    std::cout << "OpenMP max threads: " << omp_get_max_threads() << "\n";
    std::cout << "OpenMP processors reported: " << omp_get_num_procs() << "\n";

    // Task 1.1: 10 runs. Print both to console and save manually-friendly output.
    for (int run = 1; run <= 10; ++run) {
        std::cout.rdbuf(oldbuf);
        print_team_once(demo_threads, run);
        nondet << "Run " << run << ": ";
        #pragma omp parallel num_threads(demo_threads)
        {
            int tid = omp_get_thread_num();
            #pragma omp critical
            nondet << tid << ' ';
        }
        nondet << '\n';
    }

    // Task 1.2: Oversubscription sweep.
    std::vector<int> P = {1, 2, 4, 8, 16, 32, 64};
    std::ofstream csv("lab1_oversubscription.csv");
    csv << "threads,time_seconds\n";

    std::cout << "\nTask 1.2 — Oversubscription sweep\n";
    for (int threads : P) {
        // Average several repetitions because creation/join times are very small.
        const int trials = 20;
        double total = 0.0;
        for (int r = 0; r < trials; ++r) total += creation_join_time(threads);
        double avg = total / trials;
        csv << threads << ',' << std::setprecision(10) << avg << '\n';
        std::cout << "P=" << std::setw(2) << threads
                  << " | avg creation+join time = " << std::fixed << std::setprecision(8)
                  << avg << " s\n";
    }

    // Task 1.3: CPU saturation workload.
    const int saturation_threads = std::max(1, omp_get_num_procs());
    const long long work = 10'000'000LL;
    std::cout << "\nTask 1.3 — CPU saturation\n";
    std::cout << "Open Task Manager -> Performance -> CPU now.\n";
    std::cout << "Running " << saturation_threads << " threads, " << work
              << " sqrt operations per thread...\n";
    double sat_time = saturation_test(saturation_threads, work);
    std::cout << "Saturation workload finished in " << std::fixed << std::setprecision(4)
              << sat_time << " s\n";

    std::cout << "\nGenerated: lab1_nondeterminism.txt, lab1_oversubscription.csv\n";
    return 0;
}
