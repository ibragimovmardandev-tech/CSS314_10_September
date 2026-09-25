#include <omp.h>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

constexpr double PI_TRUE = 3.141592653589793238462643383279502884;

// Deliberately unsafe shared update for race-condition demonstration.
double pi_naive_race(long long N, int threads) {
    double step = 1.0 / static_cast<double>(N);
    double sum = 0.0;
    #pragma omp parallel for num_threads(threads) shared(sum)
    for (long long i = 0; i < N; ++i) {
        double x = (i + 0.5) * step;
        sum += 4.0 / (1.0 + x * x); // intentional race
    }
    return sum * step;
}

double pi_critical(long long N, int threads) {
    double step = 1.0 / static_cast<double>(N);
    double sum = 0.0;
    #pragma omp parallel for num_threads(threads) shared(sum)
    for (long long i = 0; i < N; ++i) {
        double x = (i + 0.5) * step;
        double term = 4.0 / (1.0 + x * x);
        #pragma omp critical
        sum += term;
    }
    return sum * step;
}

double pi_reduction(long long N, int threads) {
    double step = 1.0 / static_cast<double>(N);
    double sum = 0.0;
    #pragma omp parallel for num_threads(threads) reduction(+:sum)
    for (long long i = 0; i < N; ++i) {
        double x = (i + 0.5) * step;
        sum += 4.0 / (1.0 + x * x);
    }
    return sum * step;
}

double timed_reduction(long long N, int threads, double& pi_out) {
    double t0 = omp_get_wtime();
    pi_out = pi_reduction(N, threads);
    return omp_get_wtime() - t0;
}

int main() {
    omp_set_dynamic(0);
    std::cout << "LAB 2 — Numerical Integration (Pi) & Parallel Reductions\n\n";

    // Task 2.1
    const long long N_RACE = 10'000'000LL;
    std::vector<int> race_threads = {1, 2, 4, 8};
    std::ofstream race_csv("lab2_race.csv");
    race_csv << "threads,pi,error,time_seconds\n";
    std::cout << "Task 2.1 — Race Condition Quantification\n";
    for (int p : race_threads) {
        double t0 = omp_get_wtime();
        double pi = pi_naive_race(N_RACE, p);
        double t = omp_get_wtime() - t0;
        double err = std::abs(pi - PI_TRUE);
        race_csv << p << ',' << std::setprecision(15) << pi << ',' << err << ',' << t << '\n';
        std::cout << "P=" << p << " | Pi=" << std::setprecision(12) << pi
                  << " | error=" << std::scientific << err
                  << " | time=" << std::fixed << std::setprecision(4) << t << " s\n";
    }

    // Task 2.2
    const long long N_CRITICAL = 1'000'000LL;
    int crit_threads = std::min(8, std::max(2, omp_get_num_procs()));
    double t0 = omp_get_wtime();
    double pi_serial = pi_reduction(N_CRITICAL, 1);
    double t_serial = omp_get_wtime() - t0;
    t0 = omp_get_wtime();
    double pi_crit = pi_critical(N_CRITICAL, crit_threads);
    double t_crit = omp_get_wtime() - t0;
    double overhead_pct = ((t_crit - t_serial) / t_serial) * 100.0;

    std::ofstream crit_csv("lab2_critical.csv");
    crit_csv << "variant,threads,pi,time_seconds,overhead_percent\n";
    crit_csv << "serial,1," << std::setprecision(15) << pi_serial << ',' << t_serial << ",0\n";
    crit_csv << "critical," << crit_threads << ',' << pi_crit << ',' << t_crit << ',' << overhead_pct << '\n';

    std::cout << "\nTask 2.2 — Critical Section Overhead\n";
    std::cout << "Serial time   = " << t_serial << " s\n";
    std::cout << "Critical time = " << t_crit << " s\n";
    std::cout << "Lock contention overhead = " << std::fixed << std::setprecision(2)
              << overhead_pct << "%\n";

    // Task 2.3 + 2.4
    const long long N_SCALE = 100'000'000LL;
    std::vector<int> P = {1, 2, 4, 8, 16};
    const int trials = 5;
    std::vector<double> avg_times;
    std::ofstream scale_csv("lab2_scaling.csv");
    scale_csv << "threads,trial1,trial2,trial3,trial4,trial5,avg_time,speedup,efficiency\n";

    // Warm-up
    (void)pi_reduction(10000, 2);

    std::vector<std::vector<double>> all_times;
    std::vector<double> last_pi;
    for (int p : P) {
        std::vector<double> times;
        double pi = 0.0;
        for (int r = 0; r < trials; ++r) times.push_back(timed_reduction(N_SCALE, p, pi));
        double avg = 0.0;
        for (double x : times) avg += x;
        avg /= trials;
        all_times.push_back(times);
        avg_times.push_back(avg);
        last_pi.push_back(pi);
    }

    double T1 = avg_times.front();
    std::cout << "\nTask 2.3/2.4 — Strong Scaling\n";
    for (size_t i = 0; i < P.size(); ++i) {
        double speedup = T1 / avg_times[i];
        double efficiency = speedup / P[i];
        scale_csv << P[i];
        for (double x : all_times[i]) scale_csv << ',' << x;
        scale_csv << ',' << avg_times[i] << ',' << speedup << ',' << efficiency << '\n';
        std::cout << "P=" << std::setw(2) << P[i]
                  << " | avg=" << std::fixed << std::setprecision(4) << avg_times[i] << " s"
                  << " | speedup=" << std::setprecision(3) << speedup
                  << " | efficiency=" << (efficiency * 100.0) << "%"
                  << " | Pi=" << std::setprecision(12) << last_pi[i] << '\n';
    }

    std::cout << "\nGenerated: lab2_race.csv, lab2_critical.csv, lab2_scaling.csv\n";
    return 0;
}
