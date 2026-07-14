# Install Windows scheduled task: daily knowledge update at 23:00
# Run in PowerShell (may need admin for schtasks):
#   powershell -ExecutionPolicy Bypass -File scripts\install_daily_knowledge_task.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { $Py = "python" }
$Script = Join-Path $Root "scripts\daily_knowledge_update.py"
$TaskName = "AIFilmPipeline_KnowledgeUpdate_2300"

$Action = " `"$Py`" `"$Script`" --force "
# schtasks
schtasks /Create /F /TN $TaskName /SC DAILY /ST 23:00 /TR $Action /RL LIMITED
Write-Host "Created task $TaskName at 23:00 daily"
Write-Host "Command: $Action"
Write-Host "Remove: schtasks /Delete /TN $TaskName /F"
