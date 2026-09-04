# github-07-sweep-memory.ps1 - the same shape that caught cowork-alteryx-conversion,
# run against every OTHER file that ships prose ABOUT the work.
#
# WHY THIS EXISTS: the pattern scan looks for credential shapes. The two real
# leaks found on 2026-09-03 had no credential shape at all - they were English
# sentences describing client work product, and a menu naming the excluded
# skills. Nothing in a regex for tunnel hosts or GUIDs was ever going to see
# them. This sweeps for the shape that DID work: engagement vocabulary.

$ErrorActionPreference = 'Stop'

$Root     = 'C:\Users\YOURUSER\Documents\COPILOT_COWORK'
$MemDir   = Join-Path $Root 'CoworkConfig\cowork-memory'
$SkillDir = Join-Path $Root 'CoworkConfig\Skills'

# Skills excluded as engagement-shaped. Any OTHER file that names one is
# describing work that is not shipping.
$ExcludedSkills = @(
    'state-apportionment','intercompany-eliminations','tax-client-emails',
    'alteryx-to-python','je-builder','tax-provision-report-replication'
)

# Vocabulary that appears when prose describes real work for a real party,
# rather than describing a tool.
$Engagement = @(
    "the client's", 'client data', 'client file', 'client name', 'the client ',
    'engagement', 'deliverable for', 'real data', 'production data',
    'their Alteryx', 'their workbook', 'their trial balance'
)

Write-Output "SWEEP: prose that describes the work, not the tooling"
Write-Output ""

$files = @()
$files += Get-ChildItem $MemDir -Filter *.md -File -ErrorAction SilentlyContinue
$files += Get-ChildItem $SkillDir -Recurse -Filter *.md -File -ErrorAction SilentlyContinue |
          Where-Object {
              $p = $_.FullName
              $keep = $true
              foreach ($s in $ExcludedSkills) {
                  if ($p -like "*\$s\*") { $keep = $false }
              }
              $keep
          }

Write-Output ("  scanning {0} file(s) that would ship" -f $files.Count)
Write-Output ""

$flagged = New-Object System.Collections.Generic.HashSet[string]

Write-Output "--- names an EXCLUDED skill (the folder is gone; the description is not) ---"
foreach ($f in $files) {
    $txt = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $txt) { continue }
    $found = @()
    foreach ($s in $ExcludedSkills) {
        if ($txt -like "*$s*") { $found += $s }
    }
    if ($found.Count) {
        [void]$flagged.Add($f.FullName)
        Write-Output ("  {0}" -f $f.FullName.Replace("$Root\",''))
        Write-Output ("      names: {0}" -f ($found -join ', '))
    }
}
Write-Output ""

Write-Output "--- engagement vocabulary ---"
foreach ($f in $files) {
    $lines = Get-Content $f.FullName -ErrorAction SilentlyContinue
    if (-not $lines) { continue }
    $shown = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        foreach ($w in $Engagement) {
            if ($lines[$i] -like "*$w*") {
                if (-not $shown) {
                    Write-Output ("  {0}" -f $f.FullName.Replace("$Root\",''))
                    $shown = $true
                    [void]$flagged.Add($f.FullName)
                }
                $t = $lines[$i].Trim()
                if ($t.Length -gt 115) { $t = $t.Substring(0,115) + '...' }
                Write-Output ("      {0}: {1}" -f ($i+1), $t)
                break
            }
        }
    }
}
Write-Output ""

Write-Output ("SWEEP RESULT: {0} file(s) with something to read" -f $flagged.Count)
Write-Output "Nothing here is automatically a leak - read each one. The point is that"
Write-Output "a regex for credential shapes cannot see any of it."
exit 0
