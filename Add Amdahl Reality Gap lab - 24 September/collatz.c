/*
  Parallel Computing Lab 1 - Amdahl Reality Gap
  Student ID: 230103054
  Compile (GCC/MinGW): gcc -O2 -fopenmp collatz.c -o collatz.exe
  Run: collatz.exe 13054000 <physical_cores> <logical_threads>
*/

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define MOD 1000000007ULL
#define MAX_THREADS 256

typedef struct {
    double time_s;
    uint32_t max_steps;
    uint64_t checksum;
    uint64_t hits;
} RunResult;

static inline uint32_t collatz_steps(uint64_t n) {
    uint32_t steps = 0;
    while (n > 1) {
        if ((n & 1ULL) == 0) n >>= 1;
        else n = 3ULL * n + 1ULL;
        steps++;
    }
    return steps;
}

static RunResult run_seq(uint64_t N) {
    double t0 = omp_get_wtime();
    uint32_t max_steps = 0;
    uint64_t sum = 0;
    uint64_t hits = 0;
    for (uint64_t i = 1; i <= N; ++i) {
        uint32_t s = collatz_steps(i);
        if (s > max_steps) max_steps = s;
        sum += s;
        if (s > 100) hits++;
    }
    double t1 = omp_get_wtime();
    RunResult r = {t1 - t0, max_steps, sum % MOD, hits};
    return r;
}

static RunResult run_parallel(uint64_t N, int threads, omp_sched_t sched, int chunk) {
    omp_set_num_threads(threads);
    omp_set_schedule(sched, chunk);
    uint32_t max_steps = 0;
    uint64_t sum = 0;
    uint64_t hits = 0;
    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(runtime) reduction(max:max_steps) reduction(+:sum,hits)
    for (long long ii = 1; ii <= (long long)N; ++ii) {
        uint32_t s = collatz_steps((uint64_t)ii);
        if (s > max_steps) max_steps = s;
        sum += s;
        if (s > 100) hits++;
    }

    double t1 = omp_get_wtime();
    RunResult r = {t1 - t0, max_steps, sum % MOD, hits};
    return r;
}

static RunResult run_false_sharing(uint64_t N, int threads) {
    static volatile uint64_t hit_count[MAX_THREADS];
    if (threads > MAX_THREADS) threads = MAX_THREADS;
    for (int i = 0; i < MAX_THREADS; ++i) hit_count[i] = 0;

    omp_set_num_threads(threads);
    uint32_t max_steps = 0;
    uint64_t sum = 0;
    double t0 = omp_get_wtime();

    #pragma omp parallel reduction(max:max_steps) reduction(+:sum)
    {
        int tid = omp_get_thread_num();
        #pragma omp for schedule(static)
        for (long long ii = 1; ii <= (long long)N; ++ii) {
            uint32_t s = collatz_steps((uint64_t)ii);
            if (s > max_steps) max_steps = s;
            sum += s;
            if (s > 100) hit_count[tid]++;
        }
    }

    uint64_t hits = 0;
    for (int i = 0; i < threads; ++i) hits += hit_count[i];
    double t1 = omp_get_wtime();
    RunResult r = {t1 - t0, max_steps, sum % MOD, hits};
    return r;
}

static RunResult run_reduction_hits(uint64_t N, int threads) {
    omp_set_num_threads(threads);
    uint32_t max_steps = 0;
    uint64_t sum = 0;
    uint64_t total_hits = 0;
    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(static) reduction(max:max_steps) reduction(+:sum,total_hits)
    for (long long ii = 1; ii <= (long long)N; ++ii) {
        uint32_t s = collatz_steps((uint64_t)ii);
        if (s > max_steps) max_steps = s;
        sum += s;
        if (s > 100) total_hits++;
    }

    double t1 = omp_get_wtime();
    RunResult r = {t1 - t0, max_steps, sum % MOD, total_hits};
    return r;
}

static int contains(const int *a, int n, int x) {
    for (int i = 0; i < n; ++i) if (a[i] == x) return 1;
    return 0;
}

static void verify(const char *name, RunResult r, RunResult baseline) {
    if (r.checksum != baseline.checksum || r.max_steps != baseline.max_steps || r.hits != baseline.hits) {
        fprintf(stderr, "WARNING: verification mismatch in %s (checksum/max/hits)\n", name);
    }
}

int main(int argc, char **argv) {
    uint64_t N = 13054000ULL;
    int physical = 0;
    int logical = omp_get_max_threads();

    if (argc >= 2) N = strtoull(argv[1], NULL, 10);
    if (argc >= 3) physical = atoi(argv[2]);
    if (argc >= 4) logical = atoi(argv[3]);
    if (logical <= 0) logical = omp_get_max_threads();
    if (physical <= 0) physical = logical;
    if (physical > logical) physical = logical;

    printf("N=%llu | physical=%d | logical=%d | omp_max=%d\n",
           (unsigned long long)N, physical, logical, omp_get_max_threads());
    printf("Running real local benchmarks. Keep other apps closed.\n\n");

    FILE *f = fopen("results.csv", "w");
    if (!f) { perror("results.csv"); return 1; }
    fprintf(f, "experiment,variant,threads,run1,run2,run3,avg,s_emp,s_theo,delta,throughput,penalty_ratio,chunk,checksum,max_steps,hits\n");

    // Phase 2: sequential baseline, warmup + two measured runs
    RunResult seq1 = run_seq(N);
    RunResult seq2 = run_seq(N);
    RunResult seq3 = run_seq(N);
    double Tseq = (seq2.time_s + seq3.time_s) / 2.0;
    RunResult baseline = seq2;
    printf("SEQ: cold=%.6f run2=%.6f run3=%.6f avg=%.6f checksum=%llu max=%u hits=%llu\n",
           seq1.time_s, seq2.time_s, seq3.time_s, Tseq,
           (unsigned long long)baseline.checksum, baseline.max_steps, (unsigned long long)baseline.hits);
    fprintf(f, "sequential,baseline,1,%.9f,%.9f,%.9f,%.9f,1.000000000,1.000000000,0.000000000,%.3f,1.000000000,,%llu,%u,%llu\n",
            seq1.time_s, seq2.time_s, seq3.time_s, Tseq, (double)N/Tseq,
            (unsigned long long)baseline.checksum, baseline.max_steps, (unsigned long long)baseline.hits);

    // Phase 3: scaling
    int candidates[8]; int nc = 0;
    int base[] = {1,2,4,8,16};
    for (int i = 0; i < 5; ++i) if (base[i] <= logical && !contains(candidates,nc,base[i])) candidates[nc++] = base[i];
    if (physical > 0 && physical <= logical && !contains(candidates,nc,physical)) candidates[nc++] = physical;
    if (logical > 0 && !contains(candidates,nc,logical)) candidates[nc++] = logical;

    double s2 = 0.0, p = 0.0;
    typedef struct { int k; double r1,r2,r3,avg,semp; uint64_t cs; uint32_t mx; uint64_t hits; } ScaleRow;
    ScaleRow rows[8]; int nr = 0;

    for (int idx = 0; idx < nc; ++idx) {
        int k = candidates[idx];
        RunResult r1 = run_parallel(N,k,omp_sched_static,0);
        RunResult r2 = run_parallel(N,k,omp_sched_static,0);
        RunResult r3 = run_parallel(N,k,omp_sched_static,0);
        verify("scaling", r2, baseline); verify("scaling", r3, baseline);
        double avg = (r2.time_s + r3.time_s)/2.0;
        double semp = Tseq/avg;
        rows[nr++] = (ScaleRow){k,r1.time_s,r2.time_s,r3.time_s,avg,semp,r2.checksum,r2.max_steps,r2.hits};
        if (k == 2) s2 = semp;
        printf("k=%d: cold=%.6f run2=%.6f run3=%.6f avg=%.6f speedup=%.4fx\n", k,r1.time_s,r2.time_s,r3.time_s,avg,semp);
    }

    if (s2 > 0.0) p = 2.0 * (1.0 - 1.0/s2);
    printf("\nDerived p from k=2: %.9f\n", p);
    for (int i = 0; i < nr; ++i) {
        int k = rows[i].k;
        double stheo = (s2 > 0.0) ? 1.0 / ((1.0-p) + p/(double)k) : 0.0;
        double delta = stheo - rows[i].semp;
        fprintf(f, "scaling,static,%d,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.3f,,, %llu,%u,%llu\n",
                k,rows[i].r1,rows[i].r2,rows[i].r3,rows[i].avg,rows[i].semp,stheo,delta,
                (double)N/rows[i].avg,(unsigned long long)rows[i].cs,rows[i].mx,(unsigned long long)rows[i].hits);
    }

    // Phase 4A: false sharing vs reduction. 1 warmup + two measured runs for robustness.
    int ft = physical;
    if (ft < 1) ft = logical;
    RunResult fsw = run_false_sharing(N,ft);
    RunResult fs2 = run_false_sharing(N,ft);
    RunResult fs3 = run_false_sharing(N,ft);
    RunResult rdw = run_reduction_hits(N,ft);
    RunResult rd2 = run_reduction_hits(N,ft);
    RunResult rd3 = run_reduction_hits(N,ft);
    verify("false_sharing", fs2, baseline); verify("reduction", rd2, baseline);
    double fsavg=(fs2.time_s+fs3.time_s)/2.0, rdavg=(rd2.time_s+rd3.time_s)/2.0;
    double penalty = fsavg/rdavg;
    printf("\nFalse sharing (%d threads): %.6f s | reduction: %.6f s | penalty ratio %.4fx\n", ft,fsavg,rdavg,penalty);
    fprintf(f, "false_sharing,naive_hits_array,%d,%.9f,%.9f,%.9f,%.9f,,,,%.3f,%.9f,,%llu,%u,%llu\n",
            ft,fsw.time_s,fs2.time_s,fs3.time_s,fsavg,(double)N/fsavg,penalty,
            (unsigned long long)fs2.checksum,fs2.max_steps,(unsigned long long)fs2.hits);
    fprintf(f, "false_sharing,reduction,%d,%.9f,%.9f,%.9f,%.9f,,,,%.3f,1.000000000,,%llu,%u,%llu\n",
            ft,rdw.time_s,rd2.time_s,rd3.time_s,rdavg,(double)N/rdavg,
            (unsigned long long)rd2.checksum,rd2.max_steps,(unsigned long long)rd2.hits);

    // Phase 4B: scheduling at physical core count. Each variant: warmup + 2 measured.
    struct SchedCfg { const char *name; omp_sched_t kind; int chunk; const char *chunk_label; } cfg[] = {
        {"static", omp_sched_static, 0, "default"},
        {"static_1000", omp_sched_static, 1000, "1000"},
        {"dynamic_100", omp_sched_dynamic, 100, "100"},
        {"dynamic_10000", omp_sched_dynamic, 10000, "10000"},
        {"guided", omp_sched_guided, 0, "exponential_decay"}
    };
    printf("\nScheduling (%d threads):\n", ft);
    for (int i = 0; i < 5; ++i) {
        RunResult w = run_parallel(N,ft,cfg[i].kind,cfg[i].chunk);
        RunResult a = run_parallel(N,ft,cfg[i].kind,cfg[i].chunk);
        RunResult b = run_parallel(N,ft,cfg[i].kind,cfg[i].chunk);
        verify(cfg[i].name,a,baseline); verify(cfg[i].name,b,baseline);
        double avg=(a.time_s+b.time_s)/2.0;
        printf("  %-14s avg=%.6f s\n",cfg[i].name,avg);
        fprintf(f, "scheduling,%s,%d,%.9f,%.9f,%.9f,%.9f,,,,%.3f,,%s,%llu,%u,%llu\n",
                cfg[i].name,ft,w.time_s,a.time_s,b.time_s,avg,(double)N/avg,cfg[i].chunk_label,
                (unsigned long long)a.checksum,a.max_steps,(unsigned long long)a.hits);
    }

    fclose(f);

    FILE *m = fopen("meta.txt", "w");
    if (m) {
        fprintf(m, "student_id=230103054\nN=%llu\nphysical_cores=%d\nlogical_threads=%d\nT_seq=%.9f\nS2=%.9f\np=%.9f\nchecksum=%llu\nmax_steps=%u\nhits_gt_100=%llu\n",
                (unsigned long long)N,physical,logical,Tseq,s2,p,(unsigned long long)baseline.checksum,baseline.max_steps,(unsigned long long)baseline.hits);
        fclose(m);
    }

    printf("\nDONE: results.csv and meta.txt created.\n");
    return 0;
}
