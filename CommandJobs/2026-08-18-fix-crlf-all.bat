@echo off
REM ============================================================
REM  Normalize line endings for EVERY Cowork script, then LINT the
REM  jobs that were just written.
REM
REM  WHY THE LINT LIVES HERE (added 2026-08-31)
REM  A check only bites if it cannot be skipped. Running the linter
REM  as its own job means remembering to run it, which is the same
REM  failure mode as a written rule. But a .bat written through the
REM  8932 bridge arrives LF-only and cmd MIS-PARSES it, so this job
REM  must run before any new job can execute at all. Attaching the
REM  gate to a step that is already forced makes it unskippable.
REM  Only files this run actually normalized are linted - i.e. exactly
REM  the newly written ones.
REM
REM  Files written through the 8932 filesystem bridge arrive LF-only,
REM  and cmd mis-parses LF-only batch files (labels and branches fail
REM  in ways that look like a silent no-op - measured 2026-08-18 on the
REM  supergateway install worker, which exited 1 in under 2 seconds
REM  without writing a single line).
REM
REM  Covers: CommandJobs\*.bat  and  Startup\*.ps1
REM  Skips files already CRLF, so it is safe to re-run.
REM
REM  IT MUST SKIP ITSELF. The first version rewrote its own file while
REM  cmd was still reading it, shifting every byte offset so cmd resumed
REM  mid-word - it tried to run a command called 'eady' (from 'already').
REM  Never let a batch file edit itself.
REM
REM  THIS FILE USES NO LABELS, ON PURPOSE. Because it skips itself it can
REM  never be normalized by anything, so it must stay correct when stored
REM  LF-only. Labels and goto are exactly what breaks under LF, so this
REM  job branches with 'if errorlevel N exit /b' only. Do not add a label.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-18 - Bridge Hardening\crlf-all

powershell -NoProfile -ExecutionPolicy Bypass -Command "$paths = @('C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs\*.bat','C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\*.ps1'); $lint = 'C:\Users\YOURUSER\OneDrive\Documents\Cowork\Skills\self-improvement\scripts\job_lint.py'; $fixed=0; $ok=0; $new=@(); foreach ($p in $paths) { foreach ($f in Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue) { if ($f.Name -eq '2026-08-18-fix-crlf-all.bat') { continue }; $raw = [IO.File]::ReadAllText($f.FullName); $norm = $raw -replace \"`r`n\", \"`n\" -replace \"`n\", \"`r`n\"; if ($norm -ne $raw) { [IO.File]::WriteAllText($f.FullName, $norm); Write-Output ('normalized: ' + $f.Name); $fixed++; $new += $f.FullName } else { $ok++ } } }; Write-Output ''; Write-Output ('normalized ' + $fixed + ' file(s); ' + $ok + ' already correct'); $bats = @($new | Where-Object { $_ -like '*.bat' }); if ($bats.Count -eq 0) { Write-Output 'lint gate: nothing newly written to check'; exit 0 }; if (-not (Test-Path -LiteralPath $lint)) { Write-Output ('lint gate: CANNOT RUN - linter not found at ' + $lint); exit 2 }; Write-Output ''; Write-Output '--- LINT GATE on newly written job(s) ---'; $bad = 0; foreach ($b in $bats) { & python $lint $b; if ($LASTEXITCODE -eq 2) { Write-Output ('lint could not run on ' + $b); $bad = 2 } elseif ($LASTEXITCODE -ne 0) { if ($bad -eq 0) { $bad = 1 } } }; if ($bad -eq 2) { exit 2 }; if ($bad -eq 1) { exit 1 }; Write-Output 'lint gate: clean'; exit 0"

if errorlevel 2 echo COWORK_RESULT: FAIL lint-could-not-run
if errorlevel 2 exit /b 2
if errorlevel 1 echo COWORK_RESULT: FAIL a newly written job violates a lesson - fix it before running it
if errorlevel 1 exit /b 1
echo COWORK_RESULT: OK
exit /b 0
