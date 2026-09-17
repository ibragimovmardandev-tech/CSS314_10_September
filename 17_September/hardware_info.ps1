Write-Host "=== CPU ==="
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors

Write-Host "`n=== CACHE ==="
Get-CimInstance Win32_CacheMemory | Select-Object Level, InstalledSize, MaxCacheSize

Write-Host "`n=== MEMORY ==="
Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, Capacity, Speed, ConfiguredClockSpeed, DeviceLocator

Write-Host "`n=== OS ==="
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture

Write-Host "`n=== PYTHON ==="
python --version
