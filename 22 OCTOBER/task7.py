"""Task 7: 30M-double copy vs trigonometric kernel scalability.

Windows / built-in PowerShell. Keep task7.ps1 beside this file.
Run: python task7.py | Tee-Object -FilePath task7_output.txt
"""
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if platform.system() != "Windows":
        print("This version requires Windows PowerShell on Windows.", file=sys.stderr)
        return 1
    script = Path(__file__).with_name("task7.ps1")
    if not script.is_file():
        print("Missing task7.ps1; keep both files in the same folder.", file=sys.stderr)
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
