# TASK 3 - False Sharing Profile
# Native C# worker threads are compiled by Windows PowerShell Add-Type.
# This avoids the CPython GIL, so workers can really contend on cache lines.
# Run through Python: python task3.py | Tee-Object -FilePath task3_output.txt
param(
    [long]$Iterations = 50000000
)

$ErrorActionPreference = 'Stop'

if ($Iterations -le 0) {
    throw 'Iterations must be positive.'
}

$processors = @(Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop)
if ($processors.Count -eq 0) {
    throw 'Could not detect physical CPU cores via Win32_Processor.'
}
$physicalCores = [int](($processors | Measure-Object -Property NumberOfCores -Sum).Sum)
if ($physicalCores -le 0) {
    throw 'Physical CPU core count must be positive.'
}

$source = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

// Exactly 64 bytes per element, i.e. one cache-line-sized slot.
[StructLayout(LayoutKind.Explicit, Size = 64)]
public struct PaddedCounter
{
    [FieldOffset(0)]
    public long Value;
}

public static class Task3Benchmark
{
    private static double TimeUnpadded(int workers, long iterations)
    {
        // Required shared_counts: adjacent 8-byte counters share cache lines.
        long[] shared_counts = new long[workers];
        Thread[] threads = new Thread[workers];
        CountdownEvent ready = new CountdownEvent(workers);
        ManualResetEventSlim begin = new ManualResetEventSlim(false);

        for (int i = 0; i < workers; i++)
        {
            int slot = i;
            threads[i] = new Thread(delegate()
            {
                ready.Signal();
                begin.Wait();
                for (long j = 0; j < iterations; j++)
                {
                    long next = Volatile.Read(ref shared_counts[slot]) + 1L;
                    Volatile.Write(ref shared_counts[slot], next);
                }
            });
            threads[i].Start();
        }

        // Start all threads simultaneously; exclude setup from the timing.
        ready.Wait();
        Stopwatch stopwatch = Stopwatch.StartNew();
        begin.Set();
        foreach (Thread worker in threads) worker.Join();
        stopwatch.Stop();

        for (int i = 0; i < workers; i++)
        {
            if (shared_counts[i] != iterations)
                throw new InvalidOperationException("Incorrect unpadded count at slot " + i);
        }
        ready.Dispose();
        begin.Dispose();
        return stopwatch.Elapsed.TotalMilliseconds;
    }

    private static double TimePadded(int workers, long iterations)
    {
        // Same read/modify/write operations, but 64 bytes per slot.
        PaddedCounter[] shared_counts = new PaddedCounter[workers];
        Thread[] threads = new Thread[workers];
        CountdownEvent ready = new CountdownEvent(workers);
        ManualResetEventSlim begin = new ManualResetEventSlim(false);

        for (int i = 0; i < workers; i++)
        {
            int slot = i;
            threads[i] = new Thread(delegate()
            {
                ready.Signal();
                begin.Wait();
                for (long j = 0; j < iterations; j++)
                {
                    long next = Volatile.Read(ref shared_counts[slot].Value) + 1L;
                    Volatile.Write(ref shared_counts[slot].Value, next);
                }
            });
            threads[i].Start();
        }

        ready.Wait();
        Stopwatch stopwatch = Stopwatch.StartNew();
        begin.Set();
        foreach (Thread worker in threads) worker.Join();
        stopwatch.Stop();

        for (int i = 0; i < workers; i++)
        {
            if (shared_counts[i].Value != iterations)
                throw new InvalidOperationException("Incorrect padded count at slot " + i);
        }
        ready.Dispose();
        begin.Dispose();
        return stopwatch.Elapsed.TotalMilliseconds;
    }

    public static void Run(int physicalCores, long iterations)
    {
        if (Marshal.SizeOf(typeof(PaddedCounter)) != 64)
            throw new InvalidOperationException("PaddedCounter is not 64 bytes.");

        // Warm up C# JIT compilation without polluting measured iterations.
        TimeUnpadded(1, 1000);
        TimePadded(1, 1000);

        double unpaddedMs = TimeUnpadded(physicalCores, iterations);
        double paddedMs = TimePadded(physicalCores, iterations);

        Console.WriteLine("TASK 3 - Cache Line Contention (False Sharing)");
        Console.WriteLine("Student ID: 230103054");
        Console.WriteLine("Physical cores / worker threads: " + physicalCores);
        Console.WriteLine("Iterations per thread: " + iterations.ToString("N0"));
        Console.WriteLine("Unpadded counter size: 8 bytes");
        Console.WriteLine("Padded counter stride: 64 bytes");
        Console.WriteLine("Threading: native .NET threads (no Python GIL)");
        Console.WriteLine("Counter verification: PASS (all counters equal iterations)");
        Console.WriteLine();
        Console.WriteLine("{0,-25} | {1,16}", "Mode", "Wall Time (ms)");
        Console.WriteLine(new string('-', 45));
        Console.WriteLine("{0,-25} | {1,16:F3}", "Unpadded Shared", unpaddedMs);
        Console.WriteLine("{0,-25} | {1,16:F3}", "Padded (64-byte slots)", paddedMs);
        Console.WriteLine();
        Console.WriteLine("Execution ratio (Unpadded / Padded): {0:F3}x", unpaddedMs / paddedMs);
        if (unpaddedMs > paddedMs)
            Console.WriteLine("Observation: padded counters were faster in this run.");
        else
            Console.WriteLine("Observation: no padding benefit in this run; timings may vary.");
    }
}
'@

Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop
[Task3Benchmark]::Run($physicalCores, $Iterations)
