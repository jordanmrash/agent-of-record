@echo off
REM ============================================================
REM   ONE-CLICK COWORK BRIDGE
REM   Double-click this file (lives in Documents\COPILOT_COWORK\Startup).
REM   It opens VS Code pointed at THIS folder, which auto-starts the
REM   four bridge tasks and auto-forwards ports 8931-8934.
REM   The one thing left to do in VS Code: set each port PUBLIC in the
REM   Ports panel. Visibility does not persist across restarts.
REM   First-time installation: docs\setup.md at the repository root.
REM ============================================================

start "" code "%~dp0"
exit
