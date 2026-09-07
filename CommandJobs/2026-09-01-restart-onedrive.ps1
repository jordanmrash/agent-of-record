<#
  restart-onedrive.ps1

  Stop the OneDrive client, start it again, wait for it to settle,
  then re-test hydration on files known to be failing.

  WHY A RESTART IS THE RIGHT FIRST MOVE
  -------------------------------------
  149 dehydrated files across 18 areas of the Cowork tree; 48 of 48
  sampled failed to fetch, every one returning in about 0.03s. That
  is far too fast for a network attempt, so the client is refusing
  locally - a stuck client, not 149 corrupted files and not a
  connectivity problem. A restart clears a stuck client without
  touching the sync database, which /reset would rebuild.

  Nothing is deleted, nothing is reset, no setting is changed. The
  cloud remains the source of truth throughout.

  TRAPS DELIBERATELY AVOIDED
  --------------------------
  - %LOCALAPPDATA% expands to NOTHING under the 8933 bridge, so the
    executable path is resolved explicitly from the user profile and
    checked for existence rather than assumed.
  - The PID and its start time are recorded BEFORE anything is
    stopped, so "it restarted" can be proven by a NEW pid and a
    later start time - not asserted.
  - A graceful stop is tried first; force is a fallback, not the
    opening move.
  - Success is judged ONLY by files that previously failed now
    reading. A running process proves nothing about hydration.

    exit 0  hydration recovered
    exit 1  restarted cleanly but hydration still fails - a real finding
    exit 2  could not run - NOT a finding
#>
param(
  [Parameter(Mandatory=$true)][string]$SkillsRoot,
  [int]$SettleSeconds = 90,
  [int]$PollSeconds = 10
)

$userProfile = 'C:\Users\YOURUSER'
$candidates = @(
  (Join-Path $userProfile 'AppData\Local\Microsoft\OneDrive\OneDrive.exe'),
  'C:\Program Files\Microsoft OneDrive\OneDrive.exe',
  'C:\Program Files (x86)\Microsoft OneDrive\OneDrive.exe'
)

# Files that are KNOWN to fail right now. Small, so a fetch is quick.
$probes = @(
  'myvoice\skill-quality-report.json',
  'je-builder\skill-quality-report.json',
  'tax-client-emails\skill-quality-report.json'
) | ForEach-Object { Join-Path $SkillsRoot $_ }

function Test-Fetch([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return "MISSING" }
    try {
        $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'Read')
        try { $null = $fs.ReadByte() } finally { $fs.Dispose() }
        return "OK"
    } catch {
        return "FAIL"
    }
}

Write-Output "=== BEFORE: prove these files currently fail ==="
Write-Output "(If they already read, a restart is not warranted and this stops.)"
$preFail = 0
foreach ($p in $probes) {
    $r = Test-Fetch $p
    Write-Output ("  {0,-8} {1}" -f $r, (Split-Path $p -Leaf))
    if ($r -eq "FAIL") { $preFail++ }
}
Write-Output ""

if ($preFail -eq 0) {
    Write-Output "None of the probe files is failing, so there is nothing for a restart"
    Write-Output "to fix. Not touching the OneDrive client."
    Write-Output "COWORK_RESULT: OK no restart needed - probes already read"
    exit 0
}
Write-Output ("{0} of {1} probe files fail - proceeding." -f $preFail, $probes.Count)
Write-Output ""

Write-Output "=== THE RUNNING CLIENT, RECORDED BEFORE ANYTHING IS STOPPED ==="
$before = @(Get-Process -Name OneDrive -ErrorAction SilentlyContinue)
if ($before.Count -eq 0) {
    Write-Output "OneDrive is NOT running. That itself explains the failures."
    $oldPid = $null
} else {
    foreach ($p in $before) {
        Write-Output ("  pid {0}   started {1:yyyy-MM-dd HH:mm:ss}   {2}" -f $p.Id, $p.StartTime, $p.Path)
    }
    $oldPid = $before[0].Id
}
Write-Output ""

$exe = $null
if ($before.Count -gt 0 -and $before[0].Path) {
    $exe = $before[0].Path
} else {
    foreach ($c in $candidates) { if (Test-Path -LiteralPath $c) { $exe = $c; break } }
}
if (-not $exe) {
    Write-Output "Could not locate OneDrive.exe. Checked:"
    foreach ($c in $candidates) { Write-Output ("  " + $c) }
    Write-Output "COWORK_RESULT: CANNOTRUN OneDrive.exe not found"
    exit 2
}
Write-Output ("executable: " + $exe)
Write-Output ""

if ($before.Count -gt 0) {
    Write-Output "=== STOP: graceful first, force only if it will not close ==="
    foreach ($p in $before) {
        try {
            $null = & taskkill.exe /PID $p.Id 2>&1
            Write-Output ("  asked pid {0} to close" -f $p.Id)
        } catch {
            Write-Output ("  graceful close failed for pid {0}: {1}" -f $p.Id, $_.Exception.Message)
        }
    }
    Start-Sleep -Seconds 8
    $still = @(Get-Process -Name OneDrive -ErrorAction SilentlyContinue)
    if ($still.Count -gt 0) {
        Write-Output "  still running after a graceful request - forcing"
        foreach ($p in $still) {
            $null = & taskkill.exe /PID $p.Id /F 2>&1
            Write-Output ("  forced pid {0}" -f $p.Id)
        }
        Start-Sleep -Seconds 5
    }
    $gone = @(Get-Process -Name OneDrive -ErrorAction SilentlyContinue)
    if ($gone.Count -eq 0) { Write-Output "  stopped" } else { Write-Output "  WARNING: a OneDrive process is still present" }
    Write-Output ""
}

Write-Output "=== START ==="
try {
    Start-Process -FilePath $exe -ErrorAction Stop
    Write-Output "  launch requested"
} catch {
    Write-Output ("  could not start OneDrive: " + $_.Exception.Message)
    Write-Output "COWORK_RESULT: CANNOTRUN could not relaunch OneDrive"
    exit 2
}
Start-Sleep -Seconds 10

$after = @(Get-Process -Name OneDrive -ErrorAction SilentlyContinue)
if ($after.Count -eq 0) {
    Write-Output "  OneDrive did not come back up."
    Write-Output "COWORK_RESULT: FAIL OneDrive did not restart"
    exit 1
}
foreach ($p in $after) {
    Write-Output ("  pid {0}   started {1:yyyy-MM-dd HH:mm:ss}" -f $p.Id, $p.StartTime)
}
if ($oldPid -and ($after.Id -contains $oldPid)) {
    Write-Output ("  NOTE: pid {0} is unchanged - the process may not actually have restarted" -f $oldPid)
} else {
    Write-Output "  new pid confirmed - this is a genuinely new process"
}
Write-Output ""

Write-Output "=== SETTLE AND RE-TEST ==="
Write-Output "(Polling, because the client needs a moment before it will serve content.)"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$recovered = $false
while ($sw.Elapsed.TotalSeconds -lt $SettleSeconds) {
    Start-Sleep -Seconds $PollSeconds
    $results = @()
    foreach ($p in $probes) { $results += (Test-Fetch $p) }
    $okN = @($results | Where-Object { $_ -eq "OK" }).Count
    Write-Output ("  {0,5:N0}s  ok {1}/{2}" -f $sw.Elapsed.TotalSeconds, $okN, $probes.Count)
    if ($okN -eq $probes.Count) { $recovered = $true; break }
}
$sw.Stop()
Write-Output ""

Write-Output "=== AFTER ==="
foreach ($p in $probes) {
    $r = Test-Fetch $p
    Write-Output ("  {0,-8} {1}" -f $r, (Split-Path $p -Leaf))
}
Write-Output ""

if ($recovered) {
    Write-Output "Hydration RECOVERED. The client was stuck; a restart cleared it."
    Write-Output "Re-run the hydrate job to pull down the rest of the dehydrated files."
    Write-Output "COWORK_RESULT: OK hydration recovered after restart"
    exit 0
}

Write-Output "The client restarted cleanly but hydration STILL fails."
Write-Output "A stuck process was therefore not the cause. The next step up the ladder"
Write-Output "is onedrive.exe /reset, which rebuilds the local sync database - that is a"
Write-Output "bigger action and needs Jordan's explicit go-ahead."
Write-Output "COWORK_RESULT: FAIL restart did not restore hydration"
exit 1
