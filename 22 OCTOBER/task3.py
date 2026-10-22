"""Task 3: False sharing with truly parallel native threads on Windows.

Requires only Python and Windows PowerShell 5.1 (built into Windows 11).
The companion task3.ps1 compiles C# native .NET threads with Add-Type.
No Numba, C++ compiler, or extra Python packages are required.

Run in VS Code PowerShell terminal:
    python task3.py | Tee-Object -FilePath task3_output.txt

The original task requests 50,000,000 increments *per physical core*.
"""

import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if platform.system() != "Windows":
        print("Task 3 Windows version requires Windows PowerShell.", file=sys.stderr)
        return 1

    script = Path(__file__).with_name("task3.ps1")
    if not script.is_file():
        print("Missing task3.ps1: keep it next to task3.py.", file=sys.stderr)
        return 1

    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", str(script),
    ]
    try:
        return subprocess.call(command)
    except OSError as error:
        print(f"Failed to start Windows PowerShell: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
