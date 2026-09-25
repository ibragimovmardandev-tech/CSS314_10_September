#include <omp.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <condition_variable>
#include <cstring>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <numeric>
#include <random>
#include <thread>
#include <vector>

template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity) : capacity_(capacity) {}

    void push(T item) {
        std::unique_lock<std::mutex> lock(m_);
        not_full_.wait(lock, [&]{ return q_.size() < capacity_; });
        q_.push_back(std::move(item));
        if (q_.size() > max_occupancy_) max_occupancy_ = q_.size();
        lock.unlock();
        not_empty_.notify_one();
    }

    T pop() {
        std::unique_lock<std::mutex> lock(m_);
        not_empty_.wait(lock, [&]{ return !q_.empty(); });
        T item = std::move(q_.front());
        q_.pop_front();
        lock.unlock();
        not_full_.notify_one();
        return item;
    }

    size_t max_occupancy() const {
        std::lock_guard<std::mutex> lock(m_);
        return max_occupancy_;
    }

private:
    size_t capacity_;
    mutable std::mutex m_;
    std::condition_variable not_empty_, not_full_;
    std::deque<T> q_;
    size_t max_occupancy_ = 0;
};

struct Packet {
    int id = -1;
    std::vector<float> data;
    double created = 0.0;
    bool stop = false;
};

struct Stats {
    int id;
    float minv, maxv;
    double mean;
    uint64_t checksum;
    double latency;
};

// Simple 1D neighborhood filter repeated 'passes' times to create configurable compute load.
void compute_filter(Packet& p, int passes) {
    std::vector<float> tmp(p.data.size());
    for (int pass = 0; pass < passes; ++pass) {
        if (p.data.size() < 3) return;
        tmp[0] = p.data[0];
        tmp.back() = p.data.back();
        for (size_t i = 1; i + 1 < p.data.size(); ++i)
            tmp[i] = (p.data[i - 1] + 2.0f * p.data[i] + p.data[i + 1]) * 0.25f;
        p.data.swap(tmp);
    }
}

Stats calculate_stats(const Packet& p) {
    auto [mn, mx] = std::minmax_element(p.data.begin(), p.data.end());
    double sum = std::accumulate(p.data.begin(), p.data.end(), 0.0);
    uint64_t checksum = 1469598103934665603ULL;
    for (float v : p.data) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(v));
        checksum ^= bits;
        checksum *= 1099511628211ULL;
    }
    return {p.id, *mn, *mx, sum / p.data.size(), checksum, omp_get_wtime() - p.created};
}

struct BenchmarkResult {
    int passes;
    double seconds;
    double throughput;
    double avg_latency;
    size_t q1max, q2max;
};

BenchmarkResult run_pipeline(int packets, int packet_size, int passes, size_t queue_capacity) {
    BoundedQueue<Packet> q1(queue_capacity), q2(queue_capacity);
    std::vector<Stats> results;
    results.reserve(packets);

    std::mt19937 rng(230103054u + passes);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);

    double t0 = omp_get_wtime();

    std::thread producer([&]{
        for (int id = 0; id < packets; ++id) {
            Packet p;
            p.id = id;
            p.data.resize(packet_size);
            for (float& x : p.data) x = dist(rng);
            p.created = omp_get_wtime();
            q1.push(std::move(p));
        }
        Packet stop; stop.stop = true;
        q1.push(std::move(stop));
    });

    std::thread compute([&]{
        while (true) {
            Packet p = q1.pop();
            if (p.stop) {
                q2.push(std::move(p));
                break;
            }
            compute_filter(p, passes);
            q2.push(std::move(p));
        }
    });

    std::thread consumer([&]{
        while (true) {
            Packet p = q2.pop();
            if (p.stop) break;
            results.push_back(calculate_stats(p));
        }
    });

    producer.join();
    compute.join();
    consumer.join();

    double elapsed = omp_get_wtime() - t0;
    double latency_sum = 0.0;
    for (const auto& s : results) latency_sum += s.latency;
    double avg_latency = results.empty() ? 0.0 : latency_sum / results.size();
    return {passes, elapsed, packets / elapsed, avg_latency, q1.max_occupancy(), q2.max_occupancy()};
}

int main() {
    std::cout << "LAB 6 BONUS — 3-Stage Pipeline Parallelism\n";
    const int packets = 120;
    const int packet_size = 200'000;
    const size_t capacity = 8;
    std::vector<int> workloads = {1, 3, 6, 12};

    std::ofstream csv("lab6_pipeline.csv");
    csv << "filter_passes,total_seconds,throughput_packets_per_sec,avg_latency_seconds,q1_max_occupancy,q2_max_occupancy\n";

    for (int passes : workloads) {
        BenchmarkResult r = run_pipeline(packets, packet_size, passes, capacity);
        csv << r.passes << ',' << r.seconds << ',' << r.throughput << ',' << r.avg_latency
            << ',' << r.q1max << ',' << r.q2max << '\n';
        std::cout << "passes=" << std::setw(2) << passes
                  << " | total=" << std::fixed << std::setprecision(3) << r.seconds << " s"
                  << " | throughput=" << std::setprecision(2) << r.throughput << " packets/s"
                  << " | avg latency=" << std::setprecision(4) << r.avg_latency << " s"
                  << " | q1 max=" << r.q1max << " | q2 max=" << r.q2max << '\n';
    }

    std::cout << "Generated: lab6_pipeline.csv\n";
    return 0;
}
