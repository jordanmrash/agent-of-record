@echo off
REM ============================================================
REM   ONE-CLICK COWORK BRIDGE
REM   Double-click this file (lives in Documents\COPILOT_COWORK\Startup).
REM   It opens VS Code pointed at THIS folder, which auto-starts
REM   both servers and auto-forwards ports 8931 + 8932.
REM   You do NOT need to touch VS Code after it opens.
REM ============================================================

start "" code "%~dp0"
exit
