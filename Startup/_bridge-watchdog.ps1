# ============================================================
#  Cowork bridge watchdog
#
#  WHY: on 2026-08-18 the 8933 bridge died twice and every job was
#  blocked until Jordan was physically at the machine to re-run GO.bat.
#  This probes all four ports and restarts ONLY the ones that are dead.
#
#  Runs from Task Scheduler every 2 minutes (see _watchdog-install.ps1).
#
#  IMPORTANT - why a restart is enough:
#  The dev tunnel forwards a PORT, and that forwarding belongs to VS Code,
#  not to the bridge process. If only the bridge process died while VS Code
#  is still open, restarting the listener restores service WITHOUT needing
#  the Ports panel to be set Public again. If VS Code itself is closed,
#  this cannot help - that still needs GO.bat.
#
#  SAFETY: it never kills anything. It only starts a listener on a port
#  that is refusing connections, and it will not restart the same port
#  more than once per cooldown window.
#
#  2026-08-21: the restart flags are now PER PORT and must stay in sync
#  with Startup\.vscode\tasks.json. Only 8931 gets --stateful (it needs a
#  persistent child to hold the Edge SSO profile lock). 8932 and 8933 run
#  STATELESS - the 30-minute idle expiry silently dropped all three tool
#  surfaces mid-session, and stateful also killed 8933 on jobs over ~60s.
#  This script previously hard-coded --stateful for all three, so any
#  watchdog restart of 8932/8933 silently reverted that fix.
#
#  2026-09-02: ADDED 8934, the Power Automate bridge. It was built on
#  2026-09-02 and tasks.json starts it, but this watchdog only knew about
#  three ports - so a dead flow bridge would have stayed dead until the
#  next GO.bat. It follows the 8932/8933 STATELESS pattern, matching its
#  tasks.json entry, which has no --stateful and no --sessionTimeout.
#  Statelessness is also load-bearing for that bridge specifically: the
#  server is re-spawned per call, which is why editing flow-mcp-server.js
#  takes effect without a restart.
# ============================================================

$Startup    = "C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup"
$LogDir     = "C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-18 - Bridge Hardening\watchdog"
$LogFile    = Join-Path $LogDir "watchdog.log"
$StatusFile = Join-Path $LogDir "status.txt"
$StateFile  = Join-Path $LogDir "_last-restart.json"
$CooldownSeconds = 300
$MaxLogLines = 500

$Bridges = @(
    @{ Port = 8931; Name = "Playwright"; Stdio = "$Startup\pw-server.cmd";   Stateful = $true  },
    @{ Port = 8932; Name = "Filesystem"; Stdio = "$Startup\fs-server.cmd";   Stateful = $false },
    @{ Port = 8933; Name = "Command";    Stdio = "$Startup\exec-server.cmd"; Stateful = $false },
    @{ Port = 8934; Name = "FlowAuto";   Stdio = "$Startup\flow-server.cmd"; Stateful = $false }
)

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch { return $false } finally { $client.Close() }
}

$lastRestart = @{}
if (Test-Path $StateFile) {
    try {
        (Get-Content $StateFile -Raw | ConvertFrom-Json).PSObject.Properties |
            ForEach-Object { $lastRestart[$_.Name] = [datetime]$_.Value }
    } catch { $lastRestart = @{} }
}

$localBin = Join-Path $Startup "node_modules\.bin\supergateway.cmd"
$useLocal = Test-Path $localBin

$statusLines = @()
$statusLines += "Cowork bridge status - checked {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
$statusLines += "supergateway source: " + $(if ($useLocal) { "local (pinned)" } else { "npx (registry)" })
$statusLines += ""

foreach ($b in $Bridges) {
    $port = $b.Port
    $alive = Test-Port $port

    if ($alive) {
        $statusLines += ("{0}  {1,-10}  UP" -f $port, $b.Name)
        continue
    }

    $key = "$port"
    if ($lastRestart.ContainsKey($key) -and ((Get-Date) - $lastRestart[$key]).TotalSeconds -lt $CooldownSeconds) {
        $statusLines += ("{0}  {1,-10}  DOWN - in cooldown, not restarted again" -f $port, $b.Name)
        Write-Log "$port $($b.Name) DOWN but inside cooldown window - left alone"
        continue
    }

    Write-Log "$port $($b.Name) DOWN - restarting"

    $sgArgs = @(
        "--port", "$port",
        "--outputTransport", "streamableHttp"
    )
    if ($b.Stateful) {
        $sgArgs += @("--stateful", "--sessionTimeout", "1800000")
        Write-Log "$port $($b.Name) restarting STATEFUL (matches tasks.json)"
    } else {
        Write-Log "$port $($b.Name) restarting STATELESS (matches tasks.json)"
    }
    $sgArgs += @("--stdio", $b.Stdio)

    try {
        if ($useLocal) {
            Start-Process -FilePath $localBin -ArgumentList $sgArgs -WorkingDirectory $Startup -WindowStyle Hidden
        } else {
            Start-Process -FilePath "npx.cmd" -ArgumentList (@("-y","supergateway") + $sgArgs) -WorkingDirectory $Startup -WindowStyle Hidden
        }
        $lastRestart[$key] = Get-Date

        Start-Sleep -Seconds 8
        if (Test-Port $port) {
            Write-Log "$port $($b.Name) RESTARTED OK"
            $statusLines += ("{0}  {1,-10}  RESTARTED just now by watchdog" -f $port, $b.Name)
        } else {
            Write-Log "$port $($b.Name) restart attempted but port still refusing - VS Code may be closed; needs GO.bat"
            $statusLines += ("{0}  {1,-10}  DOWN - restart failed, needs GO.bat" -f $port, $b.Name)
        }
    } catch {
        Write-Log "$port $($b.Name) restart threw: $($_.Exception.Message)"
        $statusLines += ("{0}  {1,-10}  DOWN - restart error" -f $port, $b.Name)
    }
}

$lastRestart | ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8
$statusLines += ""
$statusLines += "Log: watchdog.log"
$statusLines -join "`r`n" | Set-Content -Path $StatusFile -Encoding UTF8

if (Test-Path $LogFile) {
    $lines = @(Get-Content $LogFile)
    if ($lines.Count -gt $MaxLogLines) {
        $lines[-$MaxLogLines..-1] | Set-Content -Path $LogFile -Encoding UTF8
    }
}

Write-Output ($statusLines -join "`r`n")
exit 0
