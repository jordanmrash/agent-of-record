@echo off
REM ============================================================
REM  bridge-autorecover.bat
REM  MEASURE the three bridges, then let bridge_policy.py decide
REM  whether an automatic restart is authorised. Jordan authorised
REM  automatic start/restart on 2026-08-30; the BOUNDS live in
REM  bridge_policy.py so the decision is a tested table, not a
REM  judgement made in the moment.
REM
REM  READ THIS BEFORE RUNNING IT AT ALL:
REM  A single failed MCP call is NOT a down bridge. The error text
REM  "couldn't be reached, so its tools may be unavailable" is a
REM  PER-CALL transport failure on the devtunnel hop, measured at
REM  1-2%. On 2026-08-30 a write failed with that message and the
REM  very next call to the same bridge answered normally. Retry the
REM  call first. This job is for a bridge that fails a MEASURED
REM  probe, never for one that dropped a call.
REM
REM  Nor is a bridge missing from Cowork's TOOL SURFACE a reason to
REM  run this. The surface is fixed at session start; that is a new
REM  chat, not a restart.
REM
REM  No argument = DRY RUN: measures, reports the decision, changes
REM  nothing. Pass APPLY to actually restart.
REM
REM  This job NEVER runs bridge-restart-all.bat. That script drops
REM  all three bridges including the one executing it and leaves the
REM  tunnel ports PRIVATE - devtunnel.exe is not installed, so only
REM  Jordan can set them Public again.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-30 - Bridge Autorecover
setlocal enabledelayedexpansion
set "OUT=%COWORK_JOB_OUTPUT%"
if not defined OUT goto no_output
if not exist "%OUT%" mkdir "%OUT%"
set "REPORT=%OUT%\report.txt"
set "STATE=%OUT%\_job-state.txt"
set "MODE=%~1"
if not defined MODE set "MODE=DRYRUN"

if not exist "%STATE%" goto start_job
findstr /b /c:"STATUS=RUNNING" "%STATE%" >nul
if not errorlevel 1 goto already_running

:start_job
echo STATUS=RUNNING STARTED=%DATE% %TIME% > "%STATE%"
call :main > "%REPORT%" 2>&1
type "%REPORT%"
findstr /b /c:"COWORK_RESULT: FAIL" "%REPORT%" >nul
if not errorlevel 1 goto failed
findstr /b /c:"COWORK_RESULT: OK" "%REPORT%" >nul
if errorlevel 1 goto no_verdict
echo STATUS=DONE EXIT=0 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 0

:failed
echo STATUS=DONE EXIT=1 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 1

:no_verdict
echo BUG: no COWORK_RESULT line.
echo STATUS=DONE EXIT=2 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 2

:already_running
echo REFUSED: prior run still RUNNING.
echo COWORK_RESULT: FAIL prior run still in progress
endlocal & exit /b 3

:no_output
echo COWORK_RESULT: FAIL no output directory
endlocal & exit /b 4


REM ============================================================
:main
set "CJ=C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs"

echo === BRIDGE AUTORECOVER - mode %MODE% ===
echo Started %DATE% %TIME%
echo.

echo --- [0] POLICY SELFTEST - an untested authorisation is a rubber stamp ---
cd /d "%CJ%"
python bridge_policy_selftest.py
if errorlevel 1 goto selftest_failed
echo.

echo --- [1] MEASURE each port TWICE - one drop is not a down bridge ---
for %%P in (8931 8932 8933) do (
  set "LIS=no"
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%%P " ^| findstr LISTENING') do set "LIS=yes"
  curl -s -o nul -m 5 -w "%%{http_code}" http://127.0.0.1:%%P/mcp > "%OUT%\_a%%P.txt" 2>nul
  set /p C1=<"%OUT%\_a%%P.txt"
  ping -n 3 127.0.0.1 >nul
  curl -s -o nul -m 5 -w "%%{http_code}" http://127.0.0.1:%%P/mcp > "%OUT%\_b%%P.txt" 2>nul
  set /p C2=<"%OUT%\_b%%P.txt"
  set "ANS=no"
  if not "!C1!"=="000" if not "!C1!"=="" set "ANS=yes"
  if not "!C2!"=="000" if not "!C2!"=="" set "ANS=yes"
  set "V=down"
  if "!LIS!"=="yes" if "!ANS!"=="yes" set "V=up"
  echo   port %%P  listening=!LIS!  probe1=!C1!  probe2=!C2!  -^> !V!
  set "ST_%%P=!V!"
)
echo.
echo   Any HTTP status means the process answered. A port counts as UP if
echo   EITHER probe answered - one failure is the tunnel, not the bridge.
echo.

set "S=8931=!ST_8931!,8932=!ST_8932!,8933=!ST_8933!"
echo measured state: !S!
echo.

echo --- [2] POLICY DECISION ---
python bridge_policy.py --state "!S!"
set "RC=!errorlevel!"
echo (policy exit !RC!: 0=noaction 1=restart 2=refuse 3=error)
echo.

if "!RC!"=="0" goto noaction
if "!RC!"=="2" goto refused
if "!RC!"=="3" goto policy_error
if not "!RC!"=="1" goto policy_error

echo --- [3] RESTART AUTHORISED ---
if /i not "%MODE%"=="APPLY" goto dryrun_stop

for /f "tokens=2" %%S in ('python bridge_policy.py --state "!S!" ^| findstr /b "SCRIPT:"') do (
  echo running %%S
  call "%CJ%\%%S"
  echo   %%S returned !errorlevel!
)
echo.
echo --- [4] RE-MEASURE after the restart ---
for %%P in (8931 8932 8933) do (
  set "L2=no"
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%%P " ^| findstr LISTENING') do set "L2=yes"
  curl -s -o nul -m 5 -w "%%{http_code}" http://127.0.0.1:%%P/mcp > "%OUT%\_r%%P.txt" 2>nul
  set /p C3=<"%OUT%\_r%%P.txt"
  echo   port %%P  listening=!L2!  http=!C3!
)
echo.
echo REMINDER: a restarted port may need setting PUBLIC again in the VS Code
echo Ports panel - Cowork cannot do that, devtunnel.exe is absent. And the
echo restored bridge will NOT join the current chat's tool surface; that
echo needs a new chat.
echo.
echo COWORK_RESULT: OK
goto :eof

:dryrun_stop
echo DRY RUN - a restart IS authorised but nothing was run.
echo Re-run as: bridge-autorecover.bat APPLY
echo COWORK_RESULT: OK
goto :eof

:noaction
echo Nothing to do. All three bridges are listening and answering.
echo If a tool still looks absent, that is session registration, not bridge
echo health: retry the call, then start a NEW CHAT. Restart nothing.
echo COWORK_RESULT: OK
goto :eof

:refused
echo The policy REFUSED an automatic restart for this state. That is a
echo correct outcome, not an error - see the reason above. Report and stop.
echo COWORK_RESULT: OK
goto :eof

:selftest_failed
echo bridge_policy_selftest did not pass. The authorisation is not
echo trustworthy, so no restart may be attempted.
echo COWORK_RESULT: FAIL policy-selftest-failed
goto :eof

:policy_error
echo bridge_policy.py could not decide (exit !RC!). Refusing to act.
echo COWORK_RESULT: FAIL policy-error
goto :eof
