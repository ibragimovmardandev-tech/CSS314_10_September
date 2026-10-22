# Task 5: identify measured serial/parallel crossover on the local CPU.
# Native C# threads via Parallel.For, compiled by built-in Windows PowerShell.
$ErrorActionPreference = 'Stop'
$source = @'
using System;
using System.Diagnostics;
using System.Threading.Tasks;

public static class Task5Crossover
{
    private const double A = 1.713;
    private const double B = 0.425;

    private static void Range(double[] x, double[] y, int from, int to)
    {
        for (int i = from; i < to; i++) y[i] = A * x[i] + B;
    }

    private static void Kernel(double[] x, double[] y, int workers)
    {
        int n = x.Length;
        if (workers == 1)
        {
            Range(x, y, 0, n);
            return;
        }
        ParallelOptions options = new ParallelOptions();
        options.MaxDegreeOfParallelism = workers;
        Parallel.For(0, workers, options, delegate(int id)
        {
            int begin = (int)((long)n * id / workers);
            int end = (int)((long)n * (id + 1) / workers);
            Range(x, y, begin, end);
        });
    }

    private static double Timed(double[] x, double[] y, int workers)
    {
        Stopwatch sw = Stopwatch.StartNew();
        Kernel(x, y, workers);
        sw.Stop();
        return sw.Elapsed.TotalMilliseconds;
    }

    private static double Median(double[] values)
    {
        double[] copy = (double[])values.Clone();
        Array.Sort(copy);
        return copy[copy.Length / 2];
    }

    private static void Verify(double[] x, double[] serial, double[] parallel)
    {
        for (int i = 0; i < x.Length; i++)
        {
            double expected = A * x[i] + B;
            if (serial[i] != expected || parallel[i] != expected)
                throw new InvalidOperationException("Mismatch at element " + i);
        }
    }

    public static void Run()
    {
        int workers = Environment.ProcessorCount;
        if (workers < 1) throw new InvalidOperationException("No logical CPUs detected.");
        int[] sizes = new int[] {100, 1000, 10000, 100000, 1000000, 10000000};
        double[] serialTimes = new double[sizes.Length];
        double[] parallelTimes = new double[sizes.Length];

        // Warm the JIT and thread pool with the same code paths as timed work.
        double[] warmX = new double[10000];
        double[] warmY = new double[10000];
        for (int k = 0; k < 5; k++)
        {
            Kernel(warmX, warmY, 1);
            Kernel(warmX, warmY, workers);
        }

        Console.WriteLine("TASK 5 - The Overhead Crossover Point");
        Console.WriteLine("Student ID: 230103054");
        Console.WriteLine("Logical cores / parallel workers: " + workers);
        Console.WriteLine("Kernel: y[i] = 1.713 * x[i] + 0.425 (float64)");
        Console.WriteLine("Both modes use identical native C# math; parallel mode uses Parallel.For.");
        Console.WriteLine("Times: median of 7 wall-clock runs, excluding allocation/setup.");
        Console.WriteLine();
        Console.WriteLine("{0,12} | {1,13} | {2,15} | {3,9} | {4}", "N", "Serial (ms)", "Parallel (ms)", "S/P ratio", "Faster");
        Console.WriteLine(new string('-', 75));

        for (int row = 0; row < sizes.Length; row++)
        {
            int n = sizes[row];
            double[] x = new double[n];
            double[] serial = new double[n];
            double[] parallel = new double[n];
            Random rng = new Random(230103054);
            for (int i = 0; i < n; i++) x[i] = rng.NextDouble();

            double[] serialSamples = new double[7];
            double[] parallelSamples = new double[7];
            for (int rep = 0; rep < 7; rep++)
            {
                // Alternate order to limit first/second run bias.
                if ((rep % 2) == 0)
                {
                    serialSamples[rep] = Timed(x, serial, 1);
                    parallelSamples[rep] = Timed(x, parallel, workers);
                }
                else
                {
                    parallelSamples[rep] = Timed(x, parallel, workers);
                    serialSamples[rep] = Timed(x, serial, 1);
                }
            }
            Verify(x, serial, parallel);
            serialTimes[row] = Median(serialSamples);
            parallelTimes[row] = Median(parallelSamples);
            string faster = parallelTimes[row] < serialTimes[row] ? "PARALLEL" :
                            parallelTimes[row] > serialTimes[row] ? "SERIAL" : "TIE";
            Console.WriteLine("{0,12:N0} | {1,13:F4} | {2,15:F4} | {3,9:F3} | {4}",
                n, serialTimes[row], parallelTimes[row],
                serialTimes[row] / parallelTimes[row], faster);
        }

        Console.WriteLine();
        Console.WriteLine("Validation: PASS (serial and parallel output agree for all elements)");
        bool transition = false;
        for (int k = 1; k < sizes.Length; k++)
        {
            if (parallelTimes[k - 1] >= serialTimes[k - 1] && parallelTimes[k] < serialTimes[k])
            {
                Console.WriteLine("MEASURED CROSSOVER INTERVAL: {0:N0} < N <= {1:N0} (serial -> parallel)",
                    sizes[k - 1], sizes[k]);
                transition = true;
            }
        }
        if (!transition)
            Console.WriteLine("MEASURED CROSSOVER INTERVAL: NOT OBSERVED among the six tested N values.");
        Console.WriteLine("NOTE: Only the six specified sizes were measured. An exact single-N threshold");
        Console.WriteLine("cannot be established from discrete, noisy timings; intervals are honest bounds.");
        Console.WriteLine("NOTE: If multiple crossover intervals appear, results are non-monotonic/noisy.");
    }
}
'@
Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop
[Task5Crossover]::Run()
