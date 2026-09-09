@echo off
REM ============================================================
REM  Local environment for the Windows bridge launchers.
REM  Windows twin of posix\cowork-env.example.sh.
REM
REM  Copy to cowork-env.cmd and edit. The real file is gitignored
REM  and refused by name in scripts\public_scan.py, which is what
REM  keeps your account name and folder layout out of the
REM  repository.
REM
REM      copy cowork-env.example.cmd cowork-env.cmd
REM
REM  Nothing here is required. Every launcher runs with sane
REM  defaults when this file is absent; these settings exist
REM  because the correct value differs per machine and cannot be
REM  guessed by the repository. Each launcher CALLs this file after
REM  deriving COWORK_ROOT from its own location, so a value set
REM  here wins.
REM ============================================================

REM ---- What Cowork itself loads -------------------------------
REM  Skills, copilot-instructions.md and cowork-memory. This becomes
REM  the filesystem bridge's third root, so the agent can write its
REM  own corpus directly instead of waiting on cloud replication.
REM
REM  There is no portable default. Find yours and paste it in:
REM
REM    OneDrive for Business:
REM      %USERPROFILE%\OneDrive - <Your Organization>\Documents\Cowork
REM    personal OneDrive:
REM      %USERPROFILE%\OneDrive\Documents\Cowork
REM    no cloud folder at all:
REM      leave unset - the bridge starts with two roots and the
REM      in-repo CoworkConfig\ is used instead
REM
REM set "COWORK_CONFIG_ROOT=%USERPROFILE%\OneDrive - Example\Documents\Cowork"

REM ---- Playwright ---------------------------------------------
REM  msedge (default on Windows), chrome, chromium or webkit. The
REM  profile keeps your signed-in sessions; the bridge never sees a
REM  password. Use a test account until you have watched the
REM  approval flow work.
REM set "COWORK_PW_BROWSER=msedge"
REM set "COWORK_PW_PROFILE=%USERPROFILE%\pw-sso-profile"

REM ---- Tooling root -------------------------------------------
REM  Each launcher derives this from its own location, so it is
REM  already correct for a clone in any directory. Set it only if
REM  you are deliberately pointing the bridges at a different tree.
REM set "COWORK_ROOT=%USERPROFILE%\Documents\COPILOT_COWORK"
