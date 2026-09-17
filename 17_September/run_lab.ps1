$ErrorActionPreference = "Continue"

"===== HARDWARE INFO =====" | Tee-Object -FilePath results.txt
powershell -ExecutionPolicy Bypass -File .\hardware_info.ps1 2>&1 | Tee-Object -FilePath results.txt -Append

"`n===== TASK 1 =====" | Tee-Object -FilePath results.txt -Append
python .\task1_amdahl.py 2>&1 | Tee-Object -FilePath results.txt -Append

"`n===== TASK 2 - RUN 1 =====" | Tee-Object -FilePath results.txt -Append
python .\task2_falsesharing.py 2>&1 | Tee-Object -FilePath results.txt -Append
"`n===== TASK 2 - RUN 2 =====" | Tee-Object -FilePath results.txt -Append
python .\task2_falsesharing.py 2>&1 | Tee-Object -FilePath results.txt -Append
"`n===== TASK 2 - RUN 3 =====" | Tee-Object -FilePath results.txt -Append
python .\task2_falsesharing.py 2>&1 | Tee-Object -FilePath results.txt -Append

"`n===== TASK 3 =====" | Tee-Object -FilePath results.txt -Append
python .\task3_sync.py 2>&1 | Tee-Object -FilePath results.txt -Append

"`n===== TASK 3 LOCKLESS =====" | Tee-Object -FilePath results.txt -Append
python .\task3_lockless.py 2>&1 | Tee-Object -FilePath results.txt -Append

"`n===== TASK 4 =====" | Tee-Object -FilePath results.txt -Append
python .\task4_roofline.py 2>&1 | Tee-Object -FilePath results.txt -Append

Write-Host "`nDONE. Send me the contents of results.txt"
