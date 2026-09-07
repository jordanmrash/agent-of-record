# github-11-autoscan-built.ps1
#
# WHY THIS EXISTS: on 2026-09-03 the built tree was declared clean and a client
# name was sitting in it - `client-apportionment`, in a shipped .bat file.
# Every gate missed it for a DIFFERENT reason, and the reasons matter:
#
#   denylist.local.txt   empty, so the one check designed for client names has
#                        never run at all
#   github-05 autoscan   looked for TWO-WORD PROPER NOUNS in *.md - the wrong
#                        shape (lowercase hyphenated) in the wrong file type
#   github-08 verify     checks names ALREADY FOUND. It can only ever re-prove
#                        what was already known. Circular.
#   2026-08-31 genericize removed the name from three MEMORY files and never
#                        touched CommandJobs
#
# So this scans the BUILT tree, EVERY text file type, for the shape that got
# through - and reports rare capitalised words too, since that is the other
# shape a name can take. It is a candidate generator, not a verdict.

$ErrorActionPreference = 'Stop'
$Pub = 'C:\Users\YOURUSER\Documents\COWORK_PUBLIC'

if (-not (Test-Path $Pub)) { Write-Output "CANNOT RUN: $Pub not found"; exit 2 }

$exts = @('.md','.ps1','.bat','.cmd','.js','.py','.json','.txt','.yml','.yaml')
$files = Get-ChildItem $Pub -Recurse -File |
         Where-Object { $exts -contains $_.Extension.ToLower() -and $_.FullName -notmatch '\\\.git\\' }

Write-Output "AUTOSCAN OF THE BUILT TREE - candidate names, all file types"
Write-Output ("  {0} file(s)" -f $files.Count)
Write-Output ""

# Words that are obviously ours, not a name. Kept deliberately SHORT - a big
# stoplist hides the thing being looked for.
$known = @(
  'cowork','copilot','github','powershell','windows','onedrive','sharepoint',
  'microsoft','dataverse','devtunnel','robocopy','findstr','markdown','python',
  'node','json','yaml','anthropic','claude','openai','office','outlook','teams',
  'excel','word','powerpoint','alteryx','tableau','power','automate'
)

# ---- shape 1: lowercase hyphenated compounds. THIS is the shape that got out.
$compound = @{}
foreach ($f in $files) {
    $t = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $t) { continue }
    foreach ($m in [regex]::Matches($t, '(?<![A-Za-z0-9-])([a-z]{3,})-([a-z]{3,})(?![A-Za-z0-9-])')) {
        $w = $m.Value
        if (-not $compound.ContainsKey($w)) { $compound[$w] = New-Object System.Collections.Generic.HashSet[string] }
        [void]$compound[$w].Add($f.Name)
    }
}

Write-Output "--- hyphenated lowercase compounds in 1-2 files (the client-name shape) ---"
Write-Output "    A skill or folder named after a client looks EXACTLY like this."
Write-Output ""
$compound.GetEnumerator() |
  Where-Object {
      $_.Value.Count -le 2 -and
      -not ($known | Where-Object { $_.Key -like "*$_*" })
  } |
  Sort-Object Key |
  ForEach-Object {
      Write-Output ("  {0,-42} {1} file(s): {2}" -f $_.Key, $_.Value.Count, (($_.Value | Select-Object -First 2) -join ', '))
  }
Write-Output ""

# ---- shape 2: capitalised words appearing in exactly one file
$caps = @{}
foreach ($f in $files) {
    $t = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $t) { continue }
    foreach ($m in [regex]::Matches($t, '(?<![A-Za-z])([A-Z][a-z]{3,})(?![A-Za-z])')) {
        $w = $m.Groups[1].Value
        if ($known -contains $w.ToLower()) { continue }
        if (-not $caps.ContainsKey($w)) { $caps[$w] = New-Object System.Collections.Generic.HashSet[string] }
        [void]$caps[$w].Add($f.Name)
    }
}

Write-Output "--- capitalised words appearing in exactly ONE file ---"
Write-Output "    Long list by nature. Skim for a company or a person."
Write-Output ""
$single = $caps.GetEnumerator() | Where-Object { $_.Value.Count -eq 1 } | Sort-Object Key
Write-Output ("  {0} candidate(s)" -f $single.Count)
$single | ForEach-Object {
    Write-Output ("  {0,-28} {1}" -f $_.Key, ($_.Value -join ''))
}
Write-Output ""
Write-Output "END. Candidates only - a name here is not automatically a leak,"
Write-Output "and a clean list is not a guarantee. Only the denylist is a real check."
exit 0
