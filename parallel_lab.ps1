$ErrorActionPreference = "Stop"
$resultsPath = Join-Path $PSScriptRoot "lab_results.txt"

try { Start-Transcript -Path $resultsPath -Force | Out-Null } catch {}

Write-Host "============================================================"
Write-Host "PARALLEL COMPUTING LAB - REAL LOCAL BENCHMARK"
Write-Host "============================================================"
Write-Host ""
Write-Host "TASK 1 - HOST SILICON AUDIT"
Write-Host "---------------------------"

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Write-Host ("CPU Model: " + $cpu.Name)
Write-Host ("Architecture: " + $env:PROCESSOR_ARCHITECTURE)
Write-Host ("Physical Cores: " + $cpu.NumberOfCores)
Write-Host ("Logical Cores: " + $cpu.NumberOfLogicalProcessors)
Write-Host ("Current Clock: " + $cpu.CurrentClockSpeed + " MHz")
Write-Host ("Max Clock (WMI): " + $cpu.MaxClockSpeed + " MHz")
Write-Host ("L2 Cache (WMI): " + $cpu.L2CacheSize + " KB")
Write-Host ("L3 Cache (WMI): " + $cpu.L3CacheSize + " KB")
Write-Host ("OS: " + (Get-CimInstance Win32_OperatingSystem).Caption)
Write-Host ("OS Version: " + (Get-CimInstance Win32_OperatingSystem).Version)
Write-Host ""
Write-Host "Cache entries reported by Windows:"
try {
    Get-CimInstance Win32_CacheMemory |
      Select-Object Level, CacheType, InstalledSize, MaxCacheSize |
      Format-Table -AutoSize
} catch {
    Write-Host "Cache detail query unavailable."
}
Write-Host ""

$cs = @'
using System;
using System.Diagnostics;
using System.Threading;

public class ParallelLab
{
    public static long SharedCounter = 0;
    public static readonly object SyncObj = new object();

    static bool IsPrime(int n)
    {
        if (n < 2) return false;
        if (n == 2) return true;
        if ((n & 1) == 0) return false;
        for (int d = 3; (long)d * d <= n; d += 2)
            if (n % d == 0) return false;
        return true;
    }

    static int CountPrimes(int maxN, int threadCount)
    {
        Thread[] threads = new Thread[threadCount];
        int[] counts = new int[threadCount];

        int total = maxN - 1; // numbers 2..maxN inclusive
        int chunk = total / threadCount;

        for (int i = 0; i < threadCount; i++)
        {
            int idx = i;
            int start = 2 + i * chunk;
            int end = (i == threadCount - 1) ? maxN : (start + chunk - 1);

            threads[i] = new Thread(() =>
            {
                int local = 0;
                for (int n = start; n <= end; n++)
                    if (IsPrime(n)) local++;
                counts[idx] = local;
            });
            threads[i].IsBackground = true;
        }

        for (int i = 0; i < threadCount; i++) threads[i].Start();
        for (int i = 0; i < threadCount; i++) threads[i].Join();

        int sum = 0;
        for (int i = 0; i < threadCount; i++) sum += counts[i];
        return sum;
    }

    static double TimePrimeRun(int maxN, int n, out int result)
    {
        Stopwatch sw = Stopwatch.StartNew();
        result = CountPrimes(maxN, n);
        sw.Stop();
        return sw.Elapsed.TotalSeconds;
    }

    static long RunUnlockedCounter()
    {
        SharedCounter = 0;
        Thread[] threads = new Thread[10];

        for (int i = 0; i < 10; i++)
        {
            threads[i] = new Thread(() =>
            {
                for (int j = 0; j < 1000000; j++)
                    SharedCounter++;
            });
        }

        for (int i = 0; i < 10; i++) threads[i].Start();
        for (int i = 0; i < 10; i++) threads[i].Join();
        return SharedCounter;
    }

    static long RunLockedCounter()
    {
        SharedCounter = 0;
        Thread[] threads = new Thread[10];

        for (int i = 0; i < 10; i++)
        {
            threads[i] = new Thread(() =>
            {
                for (int j = 0; j < 1000000; j++)
                {
                    lock (SyncObj)
                    {
                        SharedCounter++;
                    }
                }
            });
        }

        for (int i = 0; i < 10; i++) threads[i].Start();
        for (int i = 0; i < 10; i++) threads[i].Join();
        return SharedCounter;
    }

    public static void RunAll()
    {
        const int MAX_N = 5000000;
        int[] threadCounts = { 1, 2, 4, 8, 16, 32 };
        double[,] times = new double[threadCounts.Length, 3];

        Console.WriteLine("TASK 2 - MULTI-THREAD SCALING BENCHMARK");
        Console.WriteLine("-----------------------------------------");
        Console.WriteLine("Workload: Count prime numbers from 2 to " + MAX_N);
        Console.WriteLine("Language & Runtime: C# / .NET Threads");
        Console.WriteLine("");

        CountPrimes(100000, 1);

        for (int i = 0; i < threadCounts.Length; i++)
        {
            int n = threadCounts[i];
            for (int r = 0; r < 3; r++)
            {
                int result;
                times[i, r] = TimePrimeRun(MAX_N, n, out result);
                Console.WriteLine("N=" + n + " Run " + (r + 1) +
                                  ": " + times[i, r].ToString("F4") +
                                  " s | primes=" + result);
            }
        }

        Console.WriteLine("");
        Console.WriteLine("TASK 2 SUMMARY");
        Console.WriteLine("N | Run1 | Run2 | Run3 | Avg | Speedup | Efficiency");
        double baseAvg = (times[0,0] + times[0,1] + times[0,2]) / 3.0;
        double t1 = baseAvg;
        double t2 = 0;

        for (int i = 0; i < threadCounts.Length; i++)
        {
            int n = threadCounts[i];
            double avg = (times[i,0] + times[i,1] + times[i,2]) / 3.0;
            if (n == 2) t2 = avg;
            double speedup = baseAvg / avg;
            double efficiency = speedup / n;

            Console.WriteLine(
                n + " | " +
                times[i,0].ToString("F4") + " | " +
                times[i,1].ToString("F4") + " | " +
                times[i,2].ToString("F4") + " | " +
                avg.ToString("F4") + " | " +
                speedup.ToString("F3") + "x | " +
                (efficiency * 100.0).ToString("F1") + "%"
            );
        }

        Console.WriteLine("");
        Console.WriteLine("TASK 3 - UNSYNCHRONIZED SHARED COUNTER");
        Console.WriteLine("---------------------------------------");
        const long expected = 10000000;

        for (int i = 1; i <= 10; i++)
        {
            long actual = RunUnlockedCounter();
            long error = expected - actual;
            Console.WriteLine("Run #" + i + ": actual=" + actual + " | error=" + error);
        }

        Stopwatch swUnlocked = Stopwatch.StartNew();
        long unlockedValue = RunUnlockedCounter();
        swUnlocked.Stop();

        Stopwatch swLocked = Stopwatch.StartNew();
        long lockedValue = RunLockedCounter();
        swLocked.Stop();

        Console.WriteLine("");
        Console.WriteLine("Synchronization timing:");
        Console.WriteLine("Unlocked = " + swUnlocked.Elapsed.TotalMilliseconds.ToString("F2") +
                          " ms | result=" + unlockedValue);
        Console.WriteLine("Locked   = " + swLocked.Elapsed.TotalMilliseconds.ToString("F2") +
                          " ms | result=" + lockedValue);

        Console.WriteLine("");
        Console.WriteLine("TASK 4 - AMDAHL & GUSTAFSON");
        Console.WriteLine("----------------------------");
        Console.WriteLine("T1 = " + t1.ToString("F6") + " s");
        Console.WriteLine("T2 = " + t2.ToString("F6") + " s");

        double p = 2.0 * (t1 - t2) / t1;
        Console.WriteLine("p = 2*(T1-T2)/T1 = " + p.ToString("F6"));

        if (p > 0.0 && p < 1.0)
        {
            double seq = 1.0 - p;
            double smax = 1.0 / seq;
            double s64 = 1.0 / (seq + p / 64.0);
            double gust = seq + p * 64.0;

            Console.WriteLine("Sequential fraction (1-p) = " + seq.ToString("F6"));
            Console.WriteLine("Amdahl Smax = " + smax.ToString("F3") + "x");
            Console.WriteLine("Amdahl S64  = " + s64.ToString("F3") + "x");
            Console.WriteLine("Gustafson S64 = " + gust.ToString("F3") + "x");
        }
        else
        {
            Console.WriteLine("WARNING: p fell outside 0..1 due to measured scaling/noise.");
            Console.WriteLine("Re-run Task 2 and use the new measured T1/T2; do not invent values.");
        }

        Console.WriteLine("");
        Console.WriteLine("DONE. Send lab_results.txt to ChatGPT.");
    }
}
'@

Write-Host "Compiling benchmark..."
Add-Type -TypeDefinition $cs -Language CSharp -IgnoreWarnings
[ParallelLab]::RunAll()

Write-Host ""
Write-Host "IMPORTANT: Open Task Manager > Performance > CPU and take ONE screenshot"
Write-Host "while the benchmark is running, as required by the lab."
Write-Host ""
Write-Host ("Results saved to: " + $resultsPath)

try { Stop-Transcript | Out-Null } catch {}
