# Registers and immediately starts a Cowork worker as a Scheduled Task.
# Why: the 8933 executor holds run_batch_file open for the entire process
# TREE, so any worker started with start/cmd keeps the bridge call alive
# and eventually kills the bridge. Task Scheduler owns the worker instead,
# so the launcher returns in about a second.
#
# schtasks.exe defaults (No Start On Batteries / Stop On Battery Mode) make
# the task a no-op on a laptop running unplugged - measured 2026-08-18:
# Last Result 0, zero output. These settings turn that off.
param(
    [Parameter(Mandatory=$true)][string]$Script,
    [Parameter(Mandatory=$true)][string]$TaskName
)

$ErrorActionPreference = 'Stop'

$onBattery = 'unknown'
try {
    $b = Get-CimInstance -ClassName Win32_Battery -ErrorAction Stop | Select-Object -First 1
    if ($b) { $onBattery = if ($b.BatteryStatus -eq 2) { 'no (plugged in)' } else { "yes (BatteryStatus=$($b.BatteryStatus))" } }
    else { $onBattery = 'no battery present' }
} catch { $onBattery = "could not read: $($_.Exception.Message)" }
Write-Output "Running on battery: $onBattery"

$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $Script + '" WORKER')

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::FromHours(12))

Register-ScheduledTask -TaskName $TaskName -Action $action -Settings $settings -Force | Out-Null
Write-Output "Registered scheduled task: $TaskName"

Start-ScheduledTask -TaskName $TaskName
Write-Output "Started scheduled task: $TaskName"
exit 0
