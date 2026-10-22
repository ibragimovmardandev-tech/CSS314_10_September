"""Task 6: four real .NET threads demonstrate an unsafe shared counter.

Windows / built-in PowerShell. Keep task6.ps1 beside this file.
Run: python task6.py | Tee-Object -FilePath task6_output.txt
"""
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if platform.system() != "Windows":
        print("This version requires Windows PowerShell on Windows.", file=sys.stderr)
        return 1
    script = Path(__file__).with_name("task6.ps1")
    if not script.is_file():
        print("Missing task6.ps1; keep both files in the same folder.", file=sys.stderr)
        return 1
    try:
        return subprocess.call([
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-File", str(script)
        ])
    except OSError as exc:
        print("Could not launch PowerShell: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
