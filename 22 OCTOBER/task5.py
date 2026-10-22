"""Task 5: vector-kernel serial vs all-logical-core .NET parallel benchmark.

Windows 11 / VS Code / built-in Windows PowerShell 5.1. No pip installs.
Keep task5.ps1 alongside this Python file.
Run from PowerShell:
    python task5.py | Tee-Object -FilePath task5_output.txt
"""
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if platform.system() != "Windows":
        print("This version requires Windows PowerShell on Windows.", file=sys.stderr)
        return 1
    script = Path(__file__).with_name("task5.ps1")
    if not script.is_file():
        print("Missing task5.ps1; keep both files in the same folder.", file=sys.stderr)
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
