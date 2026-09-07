# 02-build-clean-repo.ps1 - build COWORK_PUBLIC by copying named folders IN.
#
# THE RULE THIS ENFORCES: never clone-and-filter. A repo whose history has held
# engagement content can never become the published one - deleting a path in a
# new commit leaves it in every prior commit and every clone. So the public repo
# is built fresh, from an explicit include list, with no history carried over.
#
# Destination is OUTSIDE COPILOT_COWORK on purpose: cowork-close.bat runs
# `git add -A`, so a build inside the working repo would be swept into its next
# commit.
#
# CHANGED 2026-09-03, after measuring the source tree:
#   CommandJobs holds 291 script files and 270 are DATE-PREFIXED session
#   archaeology - one-off probes from a specific afternoon. They are not
#   tooling, they are what tooling looked like while it was being figured out,
#   and 8 of them carry a live Dataverse org URL. So CommandJobs now ships by
#   an explicit ALLOW list, not by copy-everything-minus-exclusions. That is a
#   92% cut and it removes the org-URL problem at the root rather than
#   sanitising it afterwards.
#
#   A pure "drop anything date-prefixed" rule would have been wrong: two dated
#   files are load-bearing, referenced BY standing jobs. They are named below.
#
# Idempotent. Re-running refreshes the copied folders in place and leaves the
# public repo's own git history alone.
#
# Exit: 0 built, 1 refused, 2 could not run.

[CmdletBinding()]
param(
    [string]$SourceRoot = 'C:\Users\YOURUSER\Documents\COPILOT_COWORK',
    [string]$DestRoot   = 'C:\Users\YOURUSER\Documents\COWORK_PUBLIC',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($DestRoot.ToLower().StartsWith($SourceRoot.ToLower())) {
    Write-Output "REFUSED: destination is inside the source repo."
    Write-Output "  A build inside COPILOT_COWORK is swept into its next commit by"
    Write-Output "  cowork-close's git add -A. Choose a destination outside it."
    exit 1
}

# Folders copied wholesale (minus the exclusions below).
$IncludeTree = @('Startup','CoworkConfig','GitHubSetup')   # v2: GitHubSetup added - the gate ships, its *.local.txt files never do

# CommandJobs is ALLOW-LISTED file by file - see the header note.
# v2 (2026-09-03 evening): names that would disclose anything live in
# allow.local.txt (one filename per line, never committed), so this shipped
# list stays generic. Both lists are merged below.
$CommandJobsAllow = @(
    # standing tooling
    '_async-launch.ps1','_template-async-job.bat','_template-job.bat',
    'bridge_policy.py','bridge_policy_selftest.py',
    'bridge-autorecover.bat','bridge-health.bat',
    'bridge-restart-8931.bat','bridge-restart-8932.bat','bridge-restart-all.bat',
    'bridge-restore-tasksjson.bat','command-bridge-test.bat',
    'devtunnel-port-public.bat','git-init.bat','git-init.ps1',
    'README.txt',
    # the publish gate itself
    'github-01-scan.bat','github-01-scan-built.bat',
    'github-02-build.bat','github-02-build-apply.bat',
    'github-04-autoscan-names.bat','github-04-autoscan-names.ps1',
    'github-05-autoscan-orgnames.bat','github-05-autoscan-orgnames.ps1',
    'github-07-sweep-memory.bat','github-07-sweep-memory.ps1',
    'github-11-autoscan-built.bat','github-11-autoscan-built.ps1',
    # dated, but load-bearing: referenced BY a standing job or a standing rule
    '2026-08-18-fix-crlf.bat','2026-08-18-fix-crlf-all.bat',
    '2026-08-18-sync-cowork-config.bat',
    '2026-09-01-restart-onedrive.bat','2026-09-01-restart-onedrive.ps1'
)
$allowLocal = Join-Path $here 'allow.local.txt'
if (Test-Path $allowLocal) {
    $CommandJobsAllow += @(Get-Content $allowLocal | Where-Object { $_.Trim() -and -not $_.TrimStart().StartsWith('#') } | ForEach-Object { $_.Trim() })
}
# Deliberately NOT shipped though they are un-dated:
#   github-03/06/08/10/12/13   verification jobs that embed the very strings they
#                              check for (a tunnel host, a client name) - they can
#                              never ship, by construction
#   _relaunch-bridges-2026-08-21.bat  one-off recovery from a specific incident
#   _rule-probe.js                    scratch
#   fix_lessons_sections.py           one-time migration, already applied

$ExcludeDirs = @(
    'Outputs','Logs','node_modules','__pycache__','Quarantine',
    'EnvironmentDiscovery','autorun','.git','.lesson-receipts','PLUGINS',
    'state-apportionment','intercompany-eliminations','tax-client-emails',
    'alteryx-to-python','je-builder','tax-provision-report-replication',
    # ADDED 2026-09-03: demo-menu is a CATALOGUE of the six skills above. Excluding
    # the folders while shipping the menu that names and describes them is worse
    # than useless - it reads as a deliberate index. (It is also already superseded
    # by skill-menu, so this costs nothing.)
    'demo-menu','public-template',
    # v2: an empty placeholder skill folder, and any skill whose SUBSTANCE is the
    # firm's own material (brand standards, house templates) - a name change would
    # be concealment, so the folder is withheld. Add such names to excludes.local.txt
    # rather than here when the folder name itself is the disclosure.
    'power-automate'
)
$exclLocal = Join-Path $here 'excludes.local.txt'
if (Test-Path $exclLocal) {
    $ExcludeDirs += @(Get-Content $exclLocal | Where-Object { $_.Trim() -and -not $_.TrimStart().StartsWith('#') } | ForEach-Object { $_.Trim() })
}

$ExcludeFiles = @(
    '*.bak','*.backup','*-backup','*.pre-*','*.orig','*.tmp','*.log','*.zip',
    '*.env','*secret*','*credential*','*token*','*.key','*.pem',
    '_commit-msg.txt','_lessons-known-keys.txt','*.local.txt','*.local.json',
    'token-cache.json','flow-bridge.config.json',
    # ADDED 2026-09-03. THE LESSON: excluding a skill FOLDER does not exclude the
    # prose that DESCRIBES it. Both files below survived the credential-pattern
    # scan clean, because neither contains a credential shape - they contain
    # English sentences about client work product. Found only by a name-shape scan.
    'cowork-alteryx-conversion.md','cowork-skill-design.md',
    # v2: superseded drafts, staging artefacts and the unapproved fallback runner
    'SS_SKILL*','_v050_*','AUTORUN.ps1','skill-menu.cache.json','package-lock.json'
)
# v2: files that must not ship but cannot be excluded by NAME because a live
# copy with the same name is shipped elsewhere. Removed from the built tree
# after the copy.
$DeleteAfterCopy = @('Startup\batch-exec-server.js')   # obsolete loose copy; the live server is CommandBridge\batch-exec-server.js

Write-Output "BUILD CLEAN REPO"
Write-Output "  source : $SourceRoot"
Write-Output "  dest   : $DestRoot"
Write-Output "  mode   : $(if ($Apply) {'APPLY'} else {'DRY RUN - pass -Apply to write'})"
Write-Output ""
Write-Output "  trees   : $($IncludeTree -join ', ')"
Write-Output "  jobs    : $($CommandJobsAllow.Count) allow-listed CommandJobs files"
Write-Output "  exclude : $($ExcludeDirs.Count) dir pattern(s), $($ExcludeFiles.Count) file pattern(s)"
Write-Output ""

foreach ($i in $IncludeTree) {
    $p = Join-Path $SourceRoot $i
    if (-not (Test-Path $p)) { Write-Output "CANNOT RUN: missing source folder $p"; exit 2 }
}

if (-not $Apply) { Write-Output "DRY RUN - robocopy /L, nothing is written"; Write-Output "" }

# ------------------------------------------------------- wipe before build --
# CHANGED 2026-09-03, and this is the doctrine of this script applied to itself.
# The earlier version refreshed files in place and PRESERVED the public repo's
# history. Two failures follow, and both were live:
#
#   1. robocopy without /MIR never DELETES. A file that becomes excluded stays
#      in the tree forever - the new exclusion silently does nothing.
#   2. Worse: even a correct delete leaves the file in the previous COMMIT.
#      `git-deletion-does-not-sanitize-history` is the rule this repo exists to
#      honour, and preserving history here broke it in the one place it matters.
#      Commit c42b716 contained cowork-alteryx-conversion.md; rebuilding on top
#      of it and pushing would have published that file in the history of the
#      repo built specifically not to contain it.
#
# So the published tree is DISPOSABLE. It is a snapshot, not a working repo -
# its history carries no value and real risk. Every build starts from zero.
# The remote URL is the one thing worth carrying across, so it is preserved.
$savedRemote = $null
if (Test-Path $DestRoot) {
    if (Test-Path (Join-Path $DestRoot '.git')) {
        Push-Location $DestRoot
        try { $savedRemote = (& git remote get-url origin 2>$null) } catch { }
        Pop-Location
    }
    if ($Apply) {
        Write-Output "--- wiping previous build (history included - see header)"
        if ($savedRemote) { Write-Output "    remote preserved: $savedRemote" }
        Remove-Item -LiteralPath $DestRoot -Recurse -Force
        Write-Output "    removed $DestRoot"
        Write-Output ""
    } else {
        Write-Output "--- would wipe $DestRoot (including .git) before rebuilding"
        Write-Output ""
    }
}

$xd = @(); foreach ($d in $ExcludeDirs)  { $xd += '/XD'; $xd += $d }
$xf = @(); foreach ($f in $ExcludeFiles) { $xf += '/XF'; $xf += $f }

# ------------------------------------------------------------ whole trees --
foreach ($i in $IncludeTree) {
    $src = Join-Path $SourceRoot $i
    $dst = Join-Path $DestRoot   $i
    Write-Output "--- $i"
    $rcargs = @($src, $dst, '/E', '/NFL', '/NDL', '/NJH', '/NP', '/R:1', '/W:1') + $xd + $xf
    if (-not $Apply) { $rcargs += '/L' }
    $out = & robocopy.exe @rcargs 2>&1
    $rc = $LASTEXITCODE
    # robocopy 0-7 are success variants; 8+ is a real failure. Testing
    # `errorlevel 1` here would call every successful copy broken.
    if ($rc -ge 8) {
        Write-Output "  robocopy FAILED rc=$rc"
        $out | Select-Object -Last 12 | ForEach-Object { Write-Output "    $_" }
        exit 2
    }
    $tail = $out | Where-Object { $_ -match '^\s+Files\s*:' } | Select-Object -First 1
    Write-Output "  rc=$rc  $tail"
}

# ------------------------------------------------------- CommandJobs, named --
Write-Output "--- CommandJobs (allow-list)"
$srcJobs = Join-Path $SourceRoot 'CommandJobs'
$dstJobs = Join-Path $DestRoot   'CommandJobs'
$copied = 0; $missing = @()
foreach ($f in $CommandJobsAllow) {
    $s = Join-Path $srcJobs $f
    if (-not (Test-Path $s)) { $missing += $f; continue }
    if ($Apply) {
        if (-not (Test-Path $dstJobs)) { New-Item -ItemType Directory -Path $dstJobs -Force | Out-Null }
        Copy-Item $s (Join-Path $dstJobs $f) -Force
    }
    $copied++
}
Write-Output ("  {0} of {1} present{2}" -f $copied, $CommandJobsAllow.Count,
              $(if ($missing) { " - MISSING: $($missing -join ', ')" } else { '' }))

if (-not $Apply) {
    Write-Output ""
    Write-Output "DRY RUN complete. Re-run with -Apply to write."
    exit 0
}

# --------------------------------------------------------- v2: post-copy --
Write-Output ""
Write-Output "--- post-copy"
foreach ($rel in $DeleteAfterCopy) {
    $p = Join-Path $DestRoot $rel
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Force; Write-Output "  removed $rel (obsolete duplicate)" }
}

# ------------------------------------------------------------- sanitise --
# Applied to the COPY only. The source repo is never modified - those values
# are live there and the bridges need them.
Write-Output ""
Write-Output "--- sanitise"
$sanPath = Join-Path $here 'sanitize.local.txt'
if (-not (Test-Path $sanPath)) {
    Write-Output "  NO sanitize.local.txt - skipping. The tunnel host will ship AS-IS."
} else {
    $pairs = @()
    foreach ($line in (Get-Content $sanPath)) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        $i = $t.IndexOf('=')
        if ($i -lt 1) { continue }
        $pairs += ,@($t.Substring(0,$i), $t.Substring($i+1))
    }
    Write-Output ("  {0} replacement pair(s)" -f $pairs.Count)

    $textExt = @('.md','.txt','.py','.js','.json','.bat','.cmd','.ps1','.yml','.yaml','.xml','.html','.ini','.cfg')
    $touched = 0; $totalHits = 0
    Get-ChildItem $DestRoot -Recurse -File | Where-Object {
        $textExt -contains $_.Extension.ToLower() -and $_.FullName -notmatch '\\\.git\\'
    } | ForEach-Object {
        $c = $null
        try { $c = Get-Content -Raw -ErrorAction Stop $_.FullName } catch { return }
        if (-not $c) { return }
        $orig = $c
        foreach ($p in $pairs) {
            if ($c.Contains($p[0])) {
                $totalHits += ([regex]::Matches($c, [regex]::Escape($p[0]))).Count
                $c = $c.Replace($p[0], $p[1])
            }
        }
        if ($c -ne $orig) {
            [System.IO.File]::WriteAllText($_.FullName, $c, (New-Object System.Text.UTF8Encoding($false)))
            $touched++
        }
    }
    Write-Output ("  {0} file(s) rewritten, {1} replacement(s)" -f $touched, $totalHits)

    # v2: the same pairs are applied to FILE and FOLDER NAMES in the built tree,
    # deepest first, so a name that carries a sanitised token is renamed rather
    # than shipped. This is what lets a standing job keep its local name while
    # the published copy carries a neutral one.
    $renamed = 0
    Get-ChildItem $DestRoot -Recurse -Force | Where-Object { $_.FullName -notmatch '\\\.git(\\|$)' } |
        Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
        $n = $_.Name; $new = $n
        foreach ($p in $pairs) { if ($new.Contains($p[0])) { $new = $new.Replace($p[0], $p[1]) } }
        if ($new -ne $n) { Rename-Item -LiteralPath $_.FullName -NewName $new; $renamed++ }
    }
    Write-Output ("  {0} file/folder name(s) rewritten" -f $renamed)
}

# ------------------------------------------------------------- templates --
Write-Output ""
Write-Output "--- repo files"
$map = @{
    'gitattributes.template' = '.gitattributes'
    'gitignore.template'     = '.gitignore'
    'README.template.md'     = 'README.md'
    'LICENSE.template'       = 'LICENSE'
    'SECURITY.template.md'   = 'SECURITY.md'
    'CONTRIBUTING.template.md' = 'CONTRIBUTING.md'
    'CHANGELOG.template.md'  = 'CHANGELOG.md'
    'CODE_OF_CONDUCT.template.md' = 'CODE_OF_CONDUCT.md'
    'SUPPORT.template.md'    = 'SUPPORT.md'
    'NOTICE.template'        = 'NOTICE'
    'CITATION.template.cff'  = 'CITATION.cff'
    'llms.template.txt'      = 'llms.txt'
}
foreach ($k in $map.Keys) {
    $s = Join-Path $here $k
    $d = Join-Path $DestRoot $map[$k]
    if (Test-Path $s) { Copy-Item $s $d -Force; Write-Output "  wrote $($map[$k])" }
    else { Write-Output "  MISSING TEMPLATE: $k - $($map[$k]) not written" }
}

# Public-facing folders are maintained as one reusable template tree so the
# clean build gets the same docs, CI, examples, and validation scripts as this
# release without maintaining a second mapping table.
$publicTemplate = Join-Path $here 'public-template'
if (Test-Path $publicTemplate) {
    Write-Output "--- public repository template"
    $out = & robocopy.exe $publicTemplate $DestRoot /E /NFL /NDL /NJH /NP /R:1 /W:1 2>&1
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        Write-Output "  public-template copy FAILED rc=$rc"
        $out | Select-Object -Last 12 | ForEach-Object { Write-Output "    $_" }
        exit 2
    }
    Write-Output "  copied docs, examples, scripts and .github"
} else {
    Write-Output "  MISSING TEMPLATE TREE: public-template"
    exit 2
}

# ------------------------------------------------------------------- git --
Write-Output ""
Write-Output "--- git"
Push-Location $DestRoot
try {
    if (-not (Test-Path (Join-Path $DestRoot '.git'))) {
        & git init -q
        & git symbolic-ref HEAD refs/heads/main
        Write-Output "  git init, branch main - single commit, no prior history"
        if ($savedRemote) {
            & git remote add origin $savedRemote
            Write-Output "  remote restored: $savedRemote"
            Write-Output "  NOTE: history was rebuilt, so the next push must be"
            Write-Output "        git push --force-with-lease origin main"
        }
    } else {
        Write-Output "  UNEXPECTED: .git survived the wipe - history may be stale"
    }

    & git add -A
    $staged = (& git diff --cached --name-only | Measure-Object).Count
    if ($staged -eq 0) {
        Write-Output "  nothing changed - no commit"
    } else {
        $msg = "Publish Agent of Record snapshot $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        & git -c user.name="Jordan Rash" -c user.email="you@example.com" commit -q -m $msg
        if ($LASTEXITCODE -ne 0) { Write-Output "  COMMIT FAILED"; Pop-Location; exit 2 }
        Write-Output "  committed $staged file(s)"
    }

    $remote = & git remote
    if (-not $remote) {
        Write-Output "  no remote configured - add it yourself, then push:"
        Write-Output "    git remote add origin https://github.com/<you>/agent-of-record.git"
        Write-Output "    git push -u origin main"
    } else {
        Write-Output "  remote: $remote  (push is yours to run)"
    }
} finally { Pop-Location }

Write-Output ""
Write-Output "BUILT. Now run:  github-01-scan.bat Built"
Write-Output "Do not push until that scan is clean."
exit 0
