@echo off
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-18 - Bridge Async Fix\crlf-fix
REM Normalizes the async job files to CRLF. Files written through the 8932
REM filesystem bridge arrive LF-only, and cmd cannot resolve  call :label
REM in an LF-only batch file - it reports "cannot find the batch label".
REM This script has no labels of its own so it runs correctly either way.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "$j='C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs'; foreach($n in @('_template-async-job.bat','2026-08-18-async-longrun-100s.bat','2026-08-18-async-failcase.bat')){$p=Join-Path $j $n; $t=[IO.File]::ReadAllText($p); $t=$t.Replace([string][char]13,''); $t=$t.Replace([string][char]10,[string][char]13+[string][char]10); [IO.File]::WriteAllText($p,$t); Write-Output ('CRLF normalized: '+$n)}"
echo COWORK_RESULT: OK
exit /b 0
