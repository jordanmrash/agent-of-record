@echo off
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Command Bridge Test
echo COMMAND_BRIDGE_TEST_OK
if not defined COWORK_JOB_OUTPUT (
echo ERROR: COWORK_JOB_OUTPUT was not supplied by the approved batch executor. 1>&2
exit /b 2
)
if not exist "%COWORK_JOB_OUTPUT%" mkdir "%COWORK_JOB_OUTPUT%"
>"%COWORK_JOB_OUTPUT%\command-bridge-test.txt" echo COMMAND_BRIDGE_TEST_OK
exit /b 0
