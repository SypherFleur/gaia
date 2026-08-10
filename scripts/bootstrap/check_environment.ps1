$ErrorActionPreference = "Continue"

Write-Host "GAIA local environment check"
Write-Host "OS:"
Get-CimInstance Win32_OperatingSystem |
  Select-Object Caption, Version, BuildNumber, OSArchitecture |
  Format-List

Write-Host "CPU:"
Get-CimInstance Win32_Processor |
  Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, VirtualizationFirmwareEnabled |
  Format-List

Write-Host "GPU:"
Get-CimInstance Win32_VideoController |
  Select-Object Name, DriverVersion, AdapterRAM, Status |
  Format-List

Write-Host "Tool versions:"
docker version
docker compose version
node --version
npm --version
py -3.13 --version
git --version
ollama --version

