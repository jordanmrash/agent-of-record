# 01-preflight-scan.ps1 - what would ship, and what should not.
#
# READ-ONLY. Copies nothing, writes nothing except its own report.
#
# Run it TWICE:
#   -Mode Source  (default) against COPILOT_COWORK, before building
#   -Mode Built   against COWORK_PUBLIC, after building
# The two can disagree. Source predicts from the include/exclude lists; Built
# inspects what actually landed. A disagreement means an exclusion is wrong,
# which is worth knowing before a push rather than after.
#
# Exit: 0 clean, 1 findings, 2 could not run.

[CmdletBinding()]
param(
    [ValidateSet('Source','Built')] [string]$Mode = 'Source',
    [string]$SourceRoot = 'C:\Users\YOURUSER\Documents\COPILOT_COWORK',
    [string]$BuiltRoot  = 'C:\Users\YOURUSER\Documents\COWORK_PUBLIC',
    [string]$Denylist   = ''
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Denylist) { $Denylist = Join-Path $here 'denylist.local.txt' }

$root = if ($Mode -eq 'Source') { $SourceRoot } else { $BuiltRoot }

if (-not (Test-Path $root)) {
    Write-Output "CANNOT RUN: root not found: $root"
    if ($Mode -eq 'Built') { Write-Output "Build it first with 02-build-clean-repo.bat." }
    exit 2
}

# THESE LISTS MUST MIRROR 02-build-clean-repo.ps1. If they drift, the scan
# measures a different tree from the one that ships and the gate is theatre.
# Measured 2026-09-03: before this was fixed the scan reported 7 files that the
# build already excluded - flow-bridge.config.json and six dated probe jobs.
$IncludeTree = @('Startup','CoworkConfig','GitHubSetup')   # v2: mirrors 02-build-clean-repo.ps1

# CommandJobs ships by ALLOW list - 270 of its 291 script files are dated
# session archaeology, not tooling.
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

# Never copied, by name, at any depth.
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

$ExcludeFilePatterns = @(
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

# Built-in patterns. These are machine and credential shapes, not client names -
# client names come from the denylist so they never live in a committed file.
# CORRECTED 2026-09-03. The first version reported 14 blocking findings and TEN
# were noise - a placeholder in an error message, a wildcard in prose, example
# fixture data in documentation, and a CSS selector called "password". Only the
# devtunnel host was real. A check that is mostly false positives trains you to
# skip it (verifier-warns-on-proxy-not-the-defect), so each pattern below fires
# on the DEFECT rather than on a word that resembles it.
$Patterns = [ordered]@{
    # A real tunnel host has a SUBDOMAIN. Bare "devtunnels.ms" in prose, or the
    # wildcard "*.devtunnels.ms", describes the service and discloses nothing.
    'devtunnel host'     = '[A-Za-z0-9]{6,}-\d{2,5}\.[a-z0-9]+\.devtunnels\.ms'
    'bearer token'       = '(?i)bearer\s+[A-Za-z0-9\-_\.]{40,}'
    'JWT'                = 'eyJ[A-Za-z0-9\-_]{10,}\.eyJ[A-Za-z0-9\-_]{10,}'
    'client secret'      = '(?i)client[_\-]?secret\s*[:=]\s*[''"]?[A-Za-z0-9\-_~.]{8,}'
    # A password ASSIGNED a literal. Excludes a CSS/XPath selector value, which
    # contains brackets, # or a quote, and excludes template placeholders.
    'password literal'   = '(?i)password\s*[:=]\s*[''"][^''"\[\]#<>${}]{6,}[''"]'
    'absolute user path' = 'C:\\Users\\[A-Za-z0-9]+'
    'dataverse org URL'  = '[a-z][a-z0-9]{5,}\.crm\.dynamics\.com'
    'refresh token'      = '(?i)refresh[_\-]?token"\s*:\s*"[^"]{20,}'
}

# Values that are obviously not real, wherever they appear. A match containing
# one of these is dropped rather than reported - otherwise the scan flags
# documentation as a leak, and its own output as noise.
$PlaceholderValues = @(
    'pass1','pass2','pass3','changeme','yourpassword','placeholder',
    'orgXXXX','orgNNNN','yourorg','yourtestorg','yourprodorg',
    'YOUR-TUNNEL-HOST','YOURUSER','example.com'
)

$deny = @()
if (Test-Path $Denylist) {
    $deny = Get-Content $Denylist |
            Where-Object { $_.Trim() -and -not $_.TrimStart().StartsWith('#') } |
            ForEach-Object { $_.Trim() }
}

# The SANITISE list is also a scan list, and this closes a false NEGATIVE the
# tightened patterns opened. `YOUR-TUNNEL-HOST-%%P.use.devtunnels.ms` in a .bat does not
# match a host pattern expecting digits, because %%P is a batch variable - so
# the host was present and unreported. Whatever sanitize.local.txt promises to
# replace must not survive; on the Built scan this is the proof the pass ran.
$sanTerms = @()
$sanPath = Join-Path $here 'sanitize.local.txt'
if (Test-Path $sanPath) {
    foreach ($line in (Get-Content $sanPath)) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        $i = $t.IndexOf('=')
        if ($i -lt 1) { continue }
        $sanTerms += $t.Substring(0, $i)
    }
}

Write-Output "PREFLIGHT SCAN - mode $Mode"
Write-Output "root      : $root"
Write-Output "denylist  : $Denylist  ($($deny.Count) term(s))"
if ($deny.Count -eq 0) {
    Write-Output ""
    Write-Output "  WARNING: the denylist is EMPTY, so no client name is being"
    Write-Output "  scanned for. The built-in patterns below still run, but they"
    Write-Output "  cannot catch a client name. Fill in denylist.local.txt."
}
Write-Output ""

# ---------------------------------------------------------------- gather --
$dirsToScan =
    if ($Mode -eq 'Source') {
        $IncludeTree | ForEach-Object { Join-Path $root $_ } | Where-Object { Test-Path $_ }
    } else {
        @($root)
    }

$files = foreach ($d in $dirsToScan) {
    Get-ChildItem -Path $d -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $parts = $_.FullName.Substring($root.Length).Split('\')
            -not ($parts | Where-Object { $ExcludeDirs -contains $_ })
        }
}

# On Source, add ONLY the allow-listed CommandJobs files - the same set the
# build copies. Scanning all 291 would report archaeology that never ships.
if ($Mode -eq 'Source') {
    $jobsDir = Join-Path $root 'CommandJobs'
    $files = @($files) + @(
        $CommandJobsAllow |
            ForEach-Object { Join-Path $jobsDir $_ } |
            Where-Object { Test-Path $_ } |
            ForEach-Object { Get-Item $_ }
    )
    # GitHubSetup/public-template is excluded from the GitHubSetup subtree
    # because the build copies its CONTENTS to the repository root. Scan those
    # files separately so Source mode still measures everything that ships.
    $publicTemplate = Join-Path $here 'public-template'
    if (Test-Path $publicTemplate) {
        $files = @($files) + @(Get-ChildItem $publicTemplate -Recurse -File -Force)
    }
}

# Drop anything the build's file-level exclusions would remove.
$files = @($files) | Where-Object {
    $n = $_.Name
    -not ($ExcludeFilePatterns | Where-Object { $n -like $_ })
}

$files = @($files)
Write-Output ("files in scope: {0}" -f $files.Count)
if ($files.Count) {
    $mb = ($files | Measure-Object Length -Sum).Sum / 1MB
    Write-Output ("total size    : {0:N1} MB" -f $mb)
}
Write-Output ""

$findings = 0

# ------------------------------------------------------------ size limit --
Write-Output "--- files over GitHub's 100 MB hard limit ---"
$big = $files | Where-Object { $_.Length -gt 100MB }
if ($big) {
    foreach ($f in $big) {
        Write-Output ("  {0,8:N1} MB  {1}" -f ($_.Length/1MB), $f.FullName.Substring($root.Length))
        $findings++
    }
} else { Write-Output "  none" }

Write-Output ""
Write-Output "--- files over 50 MB (warn - GitHub nags above this) ---"
$mid = $files | Where-Object { $_.Length -gt 50MB -and $_.Length -le 100MB }
if ($mid) { foreach ($f in $mid) { Write-Output ("  {0,8:N1} MB  {1}" -f ($f.Length/1MB), $f.FullName.Substring($root.Length)) } }
else { Write-Output "  none" }

# ---------------------------------------------------------- content scan --
# Text only. A binary would produce noise, and a secret inside one is a
# different problem this scan does not claim to solve.
$textExt = @('.md','.txt','.py','.js','.json','.bat','.cmd','.ps1','.yml','.yaml','.xml','.csv','.html','.ini','.cfg')
$textFiles = $files | Where-Object { $textExt -contains $_.Extension.ToLower() }

Write-Output ""
Write-Output ("--- content scan over {0} text file(s) ---" -f @($textFiles).Count)

$hits = [System.Collections.ArrayList]@()

foreach ($f in $textFiles) {
    $content = $null
    try { $content = Get-Content -Raw -ErrorAction Stop $f.FullName } catch { continue }
    if (-not $content) { continue }
    $rel = $f.FullName.Substring($root.Length)

    foreach ($name in $Patterns.Keys) {
        $m = [regex]::Matches($content, $Patterns[$name])
        if (-not $m.Count) { continue }
        $real = @($m | Where-Object {
            $v = $_.Value
            # Not a real finding if the value is an obvious placeholder, or - on
            # SOURCE only - if the sanitise pass is going to remove it anyway.
            # Without this second test the same tunnel host is reported twice,
            # once blocking and once not, and the two checks contradict.
            (-not ($PlaceholderValues | Where-Object { $v -like "*$_*" })) -and
            (($Mode -eq 'Built') -or -not ($sanTerms | Where-Object { $v -like "*$_*" }))
        })
        if ($real.Count) {
            [void]$hits.Add([pscustomobject]@{ Kind=$name; File=$rel; Count=$real.Count })
        }
    }
    foreach ($term in $deny) {
        $c = ([regex]::Matches($content, [regex]::Escape($term), 'IgnoreCase')).Count
        if ($c) { [void]$hits.Add([pscustomobject]@{ Kind="DENYLIST: $term"; File=$rel; Count=$c }) }
    }
    # On SOURCE a sanitise term is EXPECTED - removing it is the build's job, and
    # calling it blocking would demand you edit the working repo, which is the
    # one thing this design avoids. On BUILT the same hit means the pass did not
    # run or did not cover this file, and that IS fatal.
    foreach ($term in $sanTerms) {
        $c = ([regex]::Matches($content, [regex]::Escape($term))).Count
        if ($c) {
            $kind = if ($Mode -eq 'Built') { "UNSANITISED: $term" } else { "will be sanitised: $term" }
            [void]$hits.Add([pscustomobject]@{ Kind=$kind; File=$rel; Count=$c })
        }
    }
}

# Path names matter as much as contents - a folder name discloses on its own.
foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length)
    foreach ($term in $deny) {
        if ($rel -match [regex]::Escape($term)) {
            [void]$hits.Add([pscustomobject]@{ Kind="DENYLIST IN PATH: $term"; File=$rel; Count=1 })
        }
    }
}

if ($hits.Count -eq 0) {
    Write-Output "  no pattern or denylist hits"
} else {
    $grouped = $hits | Group-Object Kind | Sort-Object Name
    foreach ($g in $grouped) {
        Write-Output ""
        Write-Output ("  [{0}]  {1} file(s)" -f $g.Name, $g.Count)
        foreach ($h in ($g.Group | Select-Object -First 12)) {
            Write-Output ("      {0}  x{1}" -f $h.File, $h.Count)
        }
        if ($g.Count -gt 12) { Write-Output ("      ... and {0} more" -f ($g.Count - 12)) }
    }
    # Not every hit blocks. An absolute user path is untidy, not a disclosure of
    # a third party. A sanitise term on SOURCE is a prediction, not a defect -
    # the build removes it. Everything else blocks.
    $blocking = $hits | Where-Object {
        $_.Kind -ne 'absolute user path' -and -not $_.Kind.StartsWith('will be sanitised:')
    }
    $findings += @($blocking).Count
}

Write-Output ""
Write-Output "===================================================================="
if ($findings -eq 0) {
    Write-Output "CLEAN - nothing blocking found."
    if ($Mode -eq 'Source') {
        $pending = @($hits | Where-Object { $_.Kind.StartsWith('will be sanitised:') })
        if ($pending.Count) {
            Write-Output ("{0} item(s) are left for the build's sanitise pass. The Built scan" -f $pending.Count)
            Write-Output "is what proves that pass actually ran - do not skip it."
        }
    }
    if ($deny.Count -eq 0) { Write-Output "But the denylist was empty, so this proves less than it looks." }
    exit 0
}
Write-Output ("$findings blocking finding(s). Fix these before building or pushing.")
exit 1
