@echo off
REM ============================================================
REM  COWORK STANDING JOB - gamma-tango CLOSE (git step)
REM
REM  PERMANENT. Never rewrite this file for a normal close, so no
REM  write + no CRLF pass + no extra approval. Only the run is gated.
REM
REM  TWO MODES, chosen by whether _commit-msg.txt exists:
REM    absent  -> REVIEW ONLY. Syncs, shows status and diff,
REM               commits NOTHING. Safe to run any time.
REM    present -> Syncs, stages everything, commits with that file
REM               as the message (git commit -F), then deletes it
REM               so the next run is review-only again.
REM
REM  To commit: write CommandJobs\_commit-msg.txt, then run this.
REM
REM  2026-08-30 FIX - every exit code is now TESTED.
REM  Until today this job echoed `sync exit`, `git add exit` and
REM  `git commit exit` and acted on NONE of them, then echoed
REM  COWORK_RESULT: OK and exited 0 unconditionally - AND deleted
REM  _commit-msg.txt regardless. A failed close was indistinguishable
REM  from a good one and destroyed the message needed to retry.
REM  See lesson cowork-close-reports-ok-on-failed-commit.
REM
REM  The message file is now deleted ONLY after a commit that
REM  actually succeeded. On any failure it is preserved.
REM
REM  No parenthesised if/else blocks anywhere below: %ERRORLEVEL%
REM  inside one is parse-time stale. Labels only.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\Cowork Close
setlocal
set "REPO=C:\Users\YOURUSER\Documents\COPILOT_COWORK"
set "ODCW=C:\Users\YOURUSER\OneDrive\Documents\Cowork"
set "MSG=%REPO%\CommandJobs\_commit-msg.txt"
set "SI=%ODCW%\Skills\self-improvement\scripts"
set "KNOWN=%REPO%\CommandJobs\_lessons-known-keys.txt"

echo === [1] ONEDRIVE LOCAL vs REPO - staleness check ===
dir "%ODCW%\cowork-memory\*.md" /TW /-C

echo.
echo === [2] REFRESH CoworkConfig FROM ONEDRIVE ===
call "%REPO%\CommandJobs\2026-08-18-sync-cowork-config.bat" >nul
if errorlevel 1 goto sync_failed
echo sync OK (exit code tested, not just echoed)

cd /d "%REPO%"
if errorlevel 1 goto repo_missing

echo.
echo === [3] WORKING TREE ===
git --no-pager status --short

echo.
echo === [4] DIFF STAT ===
git --no-pager diff --stat

if not exist "%MSG%" goto reviewonly

echo.
echo === [4b] LESSON DUPE GATE - a new lesson key must be dispositioned ===
REM Block-then-require-an-answer, added 2026-08-31. A rule followed in one
REM task gets overlooked in the next, so the question has to be asked at the
REM boundary rather than trusted to memory. The detector is NOT deciding
REM whether an entry duplicates another - it is measured at doing that badly
REM (0.0405 on the known case). It only makes the question unavoidable and
REM puts the nearest candidates on screen while it is asked.
REM No infinite-loop risk: this job only runs when invoked, never on a timer.
python "%SI%\lesson_dupe.py" "%ODCW%\cowork-memory\cowork-lessons.md" --gate --known "%KNOWN%"
if errorlevel 2 goto dupe_error
if errorlevel 1 goto dupe_blocked
echo dupe gate OK

echo.
echo === [5] STAGING ===
git add -A
if errorlevel 1 goto add_failed
echo git add OK

echo.
echo === [6] STAGED FILES ===
git --no-pager diff --cached --name-status

echo.
echo === [6b] GUARD - nothing quarantined may be committed ===
git --no-pager diff --cached --name-only > "%TEMP%\_close_staged.txt"
findstr /b /c:"Quarantine/" "%TEMP%\_close_staged.txt" >nul
if not errorlevel 1 goto quarantine_staged
echo Quarantine/x/probe.md > "%TEMP%\_close_probe.txt"
findstr /b /c:"Quarantine/" "%TEMP%\_close_probe.txt" >nul
if errorlevel 1 goto control_broken
echo guard OK - and its negative control still fires, so the pass means something

echo.
echo === [7] COMMIT ===
git commit -F "%MSG%"
if errorlevel 1 goto commit_failed
echo git commit OK
del /f /q "%MSG%"

echo.
echo === [8] RESULT - read back from the repo, not from intent ===
git --no-pager log --oneline -3
echo.
git --no-pager status --short
echo.
echo COWORK_RESULT: OK
endlocal
exit /b 0

:reviewonly
echo.
echo === [5] REVIEW ONLY ===
echo No _commit-msg.txt present - nothing was staged or committed.
echo To commit: write CommandJobs\_commit-msg.txt then run this job again.
echo.
echo === [6] LAST 3 COMMITS ===
git --no-pager log --oneline -3
echo.
echo COWORK_RESULT: OK
endlocal
exit /b 0

:sync_failed
echo The CoworkConfig sync reported a real failure. The repo may not hold the
echo current skills, memory or instructions, so a commit now would capture a
echo stale tree. _commit-msg.txt was NOT deleted.
echo COWORK_RESULT: FAIL sync-failed
endlocal
exit /b 1

:repo_missing
echo Could not change directory to %REPO%.
echo COWORK_RESULT: FAIL repo-unreachable
endlocal
exit /b 1

:add_failed
echo git add failed. Nothing was committed and _commit-msg.txt was NOT deleted.
echo COWORK_RESULT: FAIL git-add-failed
endlocal
exit /b 1

:quarantine_staged
echo A staged path begins with Quarantine/. Quarantined content must stay OUT
echo of version control - see lesson quarantine-destination-inside-the-repo.
echo Nothing was committed and _commit-msg.txt was NOT deleted.
echo COWORK_RESULT: FAIL quarantine-staged
endlocal
exit /b 1

:control_broken
echo The quarantine guard did not fire on a known-bad path, so its pass proves
echo nothing. Refusing to commit behind a broken check.
echo COWORK_RESULT: FAIL negative-control-failed
endlocal
exit /b 1

:dupe_blocked
echo.
echo A lesson key added since the last close has no Distinct-from line, or
echo names a neighbour it does not address. Nothing was staged or committed
echo and _commit-msg.txt was NOT deleted.
echo.
echo Fix it one of two ways, both of which leave a record:
echo   - increment Hits on the existing lesson instead of adding a new key, or
echo   - add  - **Distinct-from:** ^<existing-key^> - ^<why the mechanism differs^>
echo COWORK_RESULT: FAIL lesson-dupe-not-dispositioned
endlocal
exit /b 1

:dupe_error
echo lesson_dupe exited 2 - it could not run at all, which is NOT a finding.
echo Nothing was committed and _commit-msg.txt was NOT deleted.
echo COWORK_RESULT: FAIL lesson-dupe-could-not-run
endlocal
exit /b 1

:commit_failed
echo git commit FAILED. _commit-msg.txt has been PRESERVED at:
echo   %MSG%
echo Fix the cause and run this job again - the message is not lost.
echo COWORK_RESULT: FAIL git-commit-failed
endlocal
exit /b 1
