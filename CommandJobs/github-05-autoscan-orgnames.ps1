# The frequency cut in github-04 was the WRONG cut and it is worth saying why.
#
# A client name is RARE - it appears once or twice, in one file, months ago.
# Sorting by frequency buries it under 231 hits of the word "Key". So this pass
# takes the shape of the risk instead of its volume:
#
#   - TWO capitalised words in a row, which is what a company name looks like
#   - shown ALPHABETICALLY and in full, not top-N by count
#   - plus every single-word token that appears in ONLY ONE file, which is where
#     a one-off mention hides
#
# READ-ONLY.

$pub = 'C:\Users\YOURUSER\Documents\COWORK_PUBLIC'
if (-not (Test-Path $pub)) { Write-Output "built tree not found: $pub"; exit 2 }

$textExt = @('.md','.txt','.py','.js','.json','.bat','.cmd','.ps1','.yml','.yaml','.xml','.html','.ini','.cfg')
$files = Get-ChildItem $pub -Recurse -File |
         Where-Object { $textExt -contains $_.Extension.ToLower() -and $_.FullName -notmatch '\\\.git\\' }

# Ordinary sentence-start and technical words that pair up harmlessly.
$common = @(
 'The','This','That','These','Those','There','Then','When','What','Which','Where',
 'Why','How','And','Not','But','For','With','From','Into','Over','Under','Was','Are',
 'Every','Each','Both','All','Any','One','Two','Three','Only','Once','Also','Just',
 'Even','Same','Other','Another','First','Second','Last','Before','After','Because',
 'Since','While','Until','Unless','Rather','Instead','Never','Always','Read','Write',
 'Note','Rule','Rules','Step','Steps','Use','Add','Get','Set','Say','See','Keep',
 'Fix','New','Run','Job','Task','Test','Call','Exit','Code','Data','Name','Value',
 'True','False','Null','None','Error','Warning','Info','Debug','Pass','Fail','Warn',
 'Skip','Stop','Start','End','Begin','Done','Yes','Here','They','Wait','Retry','Join',
 'Confirm','Verify','Report','State','Content','Object','String','Math','Public',
 'Required','Created','Measured','Nothing','Distinct','Purpose','Promotion','Promoted',
 'Delivered','Evidence','Failed','Failures','Hits','Date','Pattern','Key','Worked',
 'High','Medium','Low','Writing','Running','Getting','Started','Refusal','Logs',
 'Outputs','Contradictions','Microsoft','Windows','Copilot','Cowork','Power','Automate',
 'Platform','Dataverse','SharePoint','OneDrive','Outlook','Teams','Excel','Word','Office',
 'Azure','Entra','Graph','GitHub','Git','Node','Python','PowerShell','JavaScript',
 'Playwright','Chromium','Edge','Chrome','Alteryx','Visio','Studio','Visual','Server',
 'Client','Bridge','Skill','Skills','Tool','Tools','File','Files','Folder','Path',
 'Jordan','Rash','Director','Tax','Transformation',
 'Automation','Partner','Manager','Senior','Local','Users','Program','System',
 'Flow','Flows','Agent','Plugin','Connector','Environment','Solution','Workflow',
 'Response','Request','Trigger','Action','Definition','Table','Row','Column','Cell',
 'Memory','Lesson','Lessons','Digest','Gate','Check','Scan','Build','Commit','Push',
 'Batch','Exec','Executor','Watchdog','Tunnel','Port','Host','Approved','Refused',
 'Clean','Stale','Fresh','Live','Draft','Attribution','Integrity','Guardrail',
 'Contract','Scope','Surface','Session','Chat','User','Machine','Browser','Page',
 'Config','Setup','Install','Version','Return','Result','Output','Input','Index',
 'License','Copyright','Readme','Json','Html','Http','Https','Url','Time','Line'
)

$pairs  = @{}
$single = @{}

foreach ($f in $files) {
    $c = $null
    try { $c = Get-Content -Raw -ErrorAction Stop $f.FullName } catch { continue }
    if (-not $c) { continue }
    $rel = $f.FullName.Substring($pub.Length)

    foreach ($m in [regex]::Matches($c, '\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b')) {
        $v = $m.Value
        $w = $v -split '\s+'
        # A pair is interesting only if BOTH halves are unusual. "The Bridge"
        # and "Read File" are prose; "Acme Widgets" is not.
        if ($common -contains $w[0] -or $common -contains $w[1]) { continue }
        if (-not $pairs.ContainsKey($v)) { $pairs[$v] = New-Object System.Collections.Generic.HashSet[string] }
        [void]$pairs[$v].Add($rel)
    }

    foreach ($m in [regex]::Matches($c, '\b[A-Z][a-z]{3,}\b')) {
        $v = $m.Value
        if ($common -contains $v) { continue }
        if (-not $single.ContainsKey($v)) { $single[$v] = New-Object System.Collections.Generic.HashSet[string] }
        [void]$single[$v].Add($rel)
    }
}

Write-Output ("scanned {0} text file(s)" -f $files.Count)
Write-Output ""
Write-Output "=== TWO-WORD proper nouns - the shape of a company name ==="
Write-Output "    Listed in full, alphabetically. This is the list that matters."
Write-Output ""
$sortedPairs = $pairs.Keys | Sort-Object
if ($sortedPairs) {
    foreach ($k in $sortedPairs) {
        Write-Output ("  {0,-38} in {1} file(s)" -f $k, $pairs[$k].Count)
    }
    Write-Output ""
    Write-Output ("  {0} distinct pair(s)" -f $sortedPairs.Count)
} else { Write-Output "  none" }

Write-Output ""
Write-Output "=== single words appearing in exactly ONE file ==="
Write-Output "    A one-off mention hides here. Long tail is normal; scan for a"
Write-Output "    company or a surname."
Write-Output ""
$rare = $single.GetEnumerator() | Where-Object { $_.Value.Count -eq 1 } | Sort-Object Name
$n = 0
foreach ($r in $rare) {
    if ($n -ge 120) { break }
    Write-Output ("  {0,-28} {1}" -f $r.Key, (@($r.Value)[0]))
    $n++
}
Write-Output ""
Write-Output ("  {0} single-file token(s); showing {1}" -f @($rare).Count, $n)
exit 0
