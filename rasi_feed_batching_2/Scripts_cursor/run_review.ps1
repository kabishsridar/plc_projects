# Run IronPython review of Rasi_feeds_batching2.project (headless AB 2.7).
# Close the project in Automation Builder GUI before running.
$ErrorActionPreference = "Stop"
$AbExe = "C:\Program Files\ABB\AB2.7\AutomationBuilder\Common\AutomationBuilder.exe"
$Script = Join-Path $PSScriptRoot "review_project.py"
$Log = Join-Path $PSScriptRoot "review_output\review_log.txt"
if (-not (Test-Path $AbExe)) { throw "AutomationBuilder.exe not found: $AbExe" }
if (-not (Test-Path $Script)) { throw "Review script not found: $Script" }
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "review_output") | Out-Null
Write-Host "Running review via Automation Builder..."
$argline = '--profile="Automation Builder 2.7" --noUI --runscript="' + $Script + '"'
Start-Process -FilePath $AbExe -ArgumentList $argline -Wait -NoNewWindow
if (Test-Path $Log) {
    Write-Host "---- review_log.txt ----"
    Get-Content -Path $Log
} else {
    Write-Host "No log written yet at $Log"
}