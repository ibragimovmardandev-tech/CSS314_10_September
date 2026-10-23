# TASK 2 - Pseudo-Random Generator State Bottleneck
# Windows PowerShell 5.1+; no pip, numpy, numba, or C++ build tools required.
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\task2.ps1 -StudentId 230103054
# Quick validation: add -Samples 100000

param(
    [Parameter(Mandatory=$true)][string]$StudentId,
    [long]$Samples = 40000000,
    [string]$OutputFile = (Join-Path $PSScriptRoot 'task2_output.txt')
)

$ErrorActionPreference = 'Stop'
if ($StudentId -notmatch '^[0-9]+$') { throw 'Student ID must contain digits only.' }
if ($Samples -le 0) { throw 'Samples must be a positive integer.' }
# Check that the requested independent seeds fit in 64 bits.
$numericId = [UInt64]::Parse($StudentId, [System.Globalization.CultureInfo]::InvariantCulture)
if ($numericId -gt [UInt64]::MaxValue / 10) { throw 'Student ID is too large for Student_ID * 10.' }

$source = @'
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;

namespace Task2Prng
{
    // SplitMix64 accepts full unsigned 64-bit seeds; Random(int) would lose
    // the exact seed when (Student_ID * 10) exceeds Int32.MaxValue.
    public sealed class SplitMix64
    {
        private ulong state;
        public SplitMix64(ulong seed) { state = seed; }

        public double NextDouble()
        {
            unchecked
            {
                state += 0x9E3779B97F4A7C15UL;
                ulong z = state;
                z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
                z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
                z = z ^ (z >> 31);
                return (z >> 11) * (1.0 / 9007199254740992.0);
            }
        }
    }

    public static class Benchmark
    {
        private const int Workers = 4;
        private static readonly CultureInfo C = CultureInfo.InvariantCulture;

        private sealed class Result
        {
            public long Hits;
            public double Milliseconds;
            public double Pi;
            public double Error;
        }

        private static Result Simulate(ulong studentId, long samples, bool sharedMode)
        {
            long[] hits = new long[Workers];
            Thread[] threads = new Thread[Workers];
            SplitMix64 sharedGenerator = new SplitMix64(studentId);
            object generatorMutex = new object();

            Stopwatch clock = Stopwatch.StartNew();
            for (int i = 0; i < Workers; i++)
            {
                int threadIndex = i;
                long count = samples / Workers + (threadIndex < samples % Workers ? 1L : 0L);
                threads[i] = new Thread(delegate()
                {
                    long inside = 0;
                    // EXACT required independent seed: Student_ID * 10 + thread_index.
                    // Indices are 0, 1, 2, 3.
                    ulong independentSeed = checked(studentId * 10UL + (ulong)threadIndex);
                    SplitMix64 ownGenerator = new SplitMix64(independentSeed);
                    for (long k = 0; k < count; k++)
                    {
                        double x, y;
                        if (sharedMode)
                        {
                            // All four threads contend for ONE mutable PRNG.
                            // Each (x, y) pair is serialized under the mutex.
                            lock (generatorMutex)
                            {
                                x = sharedGenerator.NextDouble();
                                y = sharedGenerator.NextDouble();
                            }
                        }
                        else
                        {
                            // Each thread has an isolated PRNG. No locking.
                            x = ownGenerator.NextDouble();
                            y = ownGenerator.NextDouble();
                        }
                        if ((x * x + y * y) <= 1.0) inside++;
                    }
                    hits[threadIndex] = inside;
                });
                threads[i].IsBackground = false;
                threads[i].Start();
            }
            for (int i = 0; i < Workers; i++) threads[i].Join();
            clock.Stop();

            long totalHits = 0;
            for (int i = 0; i < Workers; i++) totalHits += hits[i];
            Result result = new Result();
            result.Hits = totalHits;
            result.Milliseconds = clock.Elapsed.TotalMilliseconds;
            result.Pi = 4.0 * totalHits / samples;
            result.Error = Math.Abs(result.Pi - Math.PI);
            return result;
        }

        public static void Run(ulong studentId, string idString, long samples, string outputFile)
        {
            // Warm up both code paths / JIT outside benchmark measurements.
            Simulate(studentId, 4000, true);
            Simulate(studentId, 4000, false);

            Console.WriteLine("TASK 2 - Pseudo-Random Generator State Bottleneck");
            Console.WriteLine("Student ID: " + idString);
            Console.WriteLine("Samples: " + samples.ToString("N0", C));
            Console.WriteLine("Threads: 4");
            Console.WriteLine("PRNG: SplitMix64 (64-bit exact integer seeds)");
            Console.WriteLine("Independent seeds: " +
                (studentId * 10UL).ToString(C) + ", " +
                (studentId * 10UL + 1UL).ToString(C) + ", " +
                (studentId * 10UL + 2UL).ToString(C) + ", " +
                (studentId * 10UL + 3UL).ToString(C));
            Console.WriteLine("Running shared PRNG with lock...");
            Result shared = Simulate(studentId, samples, true);
            Console.WriteLine("Running independent per-thread PRNGs...");
            Result independent = Simulate(studentId, samples, false);
            double speedup = shared.Milliseconds / independent.Milliseconds;

            StringBuilder report = new StringBuilder();
            report.AppendLine("TASK 2 - Pseudo-Random Generator State Bottleneck");
            report.AppendLine("Student ID: " + idString);
            report.AppendLine("Sample points per mode: " + samples.ToString("N0", C));
            report.AppendLine("Thread count: 4");
            report.AppendLine("PRNG: SplitMix64");
            report.AppendLine("Shared PRNG: one generator, mutex around each pair of draws");
            report.AppendLine("Shared PRNG: Computed pi = " + shared.Pi.ToString("F10", C));
            report.AppendLine("Shared PRNG: Absolute error from Math.PI = " + shared.Error.ToString("F10", C));
            report.AppendLine("Shared PRNG: Wall time = " + shared.Milliseconds.ToString("F3", C) + " ms");
            report.AppendLine("Shared PRNG: Points inside circle = " + shared.Hits.ToString(C));
            report.AppendLine("Independent PRNG: seed = Student_ID * 10 + thread_index (0..3)");
            report.AppendLine("Independent PRNG: Computed pi = " + independent.Pi.ToString("F10", C));
            report.AppendLine("Independent PRNG: Absolute error from Math.PI = " + independent.Error.ToString("F10", C));
            report.AppendLine("Independent PRNG: Wall time = " + independent.Milliseconds.ToString("F3", C) + " ms");
            report.AppendLine("Independent PRNG: Points inside circle = " + independent.Hits.ToString(C));
            report.AppendLine("Speedup factor (shared / independent): " + speedup.ToString("F3", C) + "x");
            report.AppendLine("Method: Four real OS threads in both modes; wall-clock includes thread startup and join.");
            string reportText = report.ToString();
            Console.WriteLine();
            Console.WriteLine(reportText);
            File.WriteAllText(outputFile, reportText, new UTF8Encoding(false));
            Console.WriteLine("Saved: " + outputFile);
        }
    }
}
'@

# Compile the benchmark in the local Windows .NET runtime.
Add-Type -TypeDefinition $source -ReferencedAssemblies @('System.dll', 'System.Core.dll') -ErrorAction Stop
[Task2Prng.Benchmark]::Run($numericId, $StudentId, $Samples, $OutputFile)
