#include <omp.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

constexpr int WIDTH = 1920;
constexpr int HEIGHT = 1080;
constexpr int MAX_ITER = 1000;

inline int mandelbrot_pixel(int px, int py) {
    double x0 = (px - WIDTH / 2.0) * 4.0 / WIDTH;
    double y0 = (py - HEIGHT / 2.0) * 4.0 / HEIGHT;
    double x = 0.0, y = 0.0;
    int iter = 0;
    while (x * x + y * y <= 4.0 && iter < MAX_ITER) {
        double xtemp = x * x - y * y + x0;
        y = 2.0 * x * y + y0;
        x = xtemp;
        ++iter;
    }
    return iter;
}

struct RunResult {
    double seconds{};
    double imbalance{};
    long long checksum{};
    std::vector<long long> work;
};

RunResult run_schedule(omp_sched_t policy, int threads, int chunk) {
    std::vector<int> image(static_cast<size_t>(WIDTH) * HEIGHT);
    std::vector<long long> thread_work(threads, 0);
    omp_set_schedule(policy, chunk);

    double t0 = omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        int tid = omp_get_thread_num();
        long long local_work = 0;
        #pragma omp for schedule(runtime)
        for (int y = 0; y < HEIGHT; ++y) {
            for (int x = 0; x < WIDTH; ++x) {
                int v = mandelbrot_pixel(x, y);
                image[static_cast<size_t>(y) * WIDTH + x] = v;
                local_work += v; // use total escape iterations as actual computational work
            }
        }
        thread_work[tid] = local_work;
    }
    double elapsed = omp_get_wtime() - t0;

    long long minw = *std::min_element(thread_work.begin(), thread_work.end());
    long long maxw = *std::max_element(thread_work.begin(), thread_work.end());
    double avgw = std::accumulate(thread_work.begin(), thread_work.end(), 0.0) / threads;
    double imbalance = avgw > 0.0 ? (maxw - minw) / avgw : 0.0;
    long long checksum = std::accumulate(image.begin(), image.end(), 0LL);
    return {elapsed, imbalance, checksum, thread_work};
}

const char* policy_name(omp_sched_t p) {
    if (p == omp_sched_static) return "static";
    if (p == omp_sched_dynamic) return "dynamic";
    if (p == omp_sched_guided) return "guided";
    return "unknown";
}

int main() {
    omp_set_dynamic(0);
    std::cout << "LAB 3 — Work-Sharing & Loop Scheduling (Mandelbrot)\n";
    std::cout << "Image: " << WIDTH << 'x' << HEIGHT << ", max_iter=" << MAX_ITER << "\n\n";

    std::vector<int> threads_list = {2, 4, 8, 16};
    std::vector<int> chunks = {1, 16, 64, 256};
    const int trials = 3;

    std::ofstream csv("lab3_benchmark.csv");
    csv << "policy,threads,chunk,trial1,trial2,trial3,mean_seconds,imbalance,checksum\n";

    // Task 3.1 + 3.2: benchmark Static and Dynamic. Guided is included as useful comparison.
    std::vector<omp_sched_t> policies = {omp_sched_static, omp_sched_dynamic, omp_sched_guided};

    for (omp_sched_t policy : policies) {
        std::cout << "=== " << policy_name(policy) << " scheduling ===\n";
        for (int p : threads_list) {
            for (int c : chunks) {
                std::vector<double> times;
                double imbalance_sum = 0.0;
                long long checksum = 0;
                for (int r = 0; r < trials; ++r) {
                    RunResult rr = run_schedule(policy, p, c);
                    times.push_back(rr.seconds);
                    imbalance_sum += rr.imbalance;
                    checksum = rr.checksum;
                }
                double mean = std::accumulate(times.begin(), times.end(), 0.0) / trials;
                double mean_imbalance = imbalance_sum / trials;
                csv << policy_name(policy) << ',' << p << ',' << c;
                for (double x : times) csv << ',' << x;
                csv << ',' << mean << ',' << mean_imbalance << ',' << checksum << '\n';

                std::cout << "P=" << std::setw(2) << p << " C=" << std::setw(3) << c
                          << " | mean=" << std::fixed << std::setprecision(4) << mean << " s"
                          << " | imbalance=" << std::setprecision(4) << mean_imbalance << '\n';
            }
        }
        std::cout << '\n';
    }

    // Detailed per-thread work example for report.
    RunResult detail = run_schedule(omp_sched_dynamic, 8, 16);
    std::ofstream work_csv("lab3_thread_work.csv");
    work_csv << "thread,work_iterations\n";
    for (size_t i = 0; i < detail.work.size(); ++i) work_csv << i << ',' << detail.work[i] << '\n';

    std::cout << "Generated: lab3_benchmark.csv, lab3_thread_work.csv\n";
    return 0;
}
