# Derive candidate client/person/org names from the BUILT tree automatically,
# so nobody has to type a denylist.
#
# The denylist exists because a scanner cannot know which names matter. This
# inverts it: extract every name-shaped token that is NOT an obvious technology
# term and show the residue. A short benign residue is real assurance; a long
# one names exactly what to look at. READ-ONLY.

$pub = 'C:\Users\YOURUSER\Documents\COWORK_PUBLIC'
if (-not (Test-Path $pub)) { Write-Output "built tree not found: $pub"; exit 2 }

$textExt = @('.md','.txt','.py','.js','.json','.bat','.cmd','.ps1','.yml','.yaml','.xml','.html','.ini','.cfg')
$files = Get-ChildItem $pub -Recurse -File |
         Where-Object { $textExt -contains $_.Extension.ToLower() -and $_.FullName -notmatch '\\\.git\\' }

$stop = @(
 'Microsoft','Windows','Copilot','Cowork','Power','Automate','Platform','Dataverse',
 'SharePoint','OneDrive','Outlook','Teams','Excel','Word','PowerPoint','Office',
 'Azure','Entra','Graph','GitHub','Git','Node','Python','PowerShell','JavaScript',
 'Playwright','Chromium','Edge','Chrome','Firefox','Safari','Alteryx','Visio',
 'Studio','Code','Visual','Server','Client','Bridge','Skill','Skills','Tool','Tools',
 'File','Files','Folder','Path','Read','Write','Delete','Create','Update','List',
 'True','False','Null','None','Error','Warning','Info','Debug','Test','Tests',
 'Note','Rule','Rules','Step','Steps','Task','Tasks','Job','Jobs','Run','Runs',
 'The','This','That','These','Those','There','Then','When','What','Which','Where',
 'Why','How','And','Not','But','For','With','From','Into','Over','Under','Was','Are',
 'Every','Each','Both','All','Any','One','Two','Three','Four','Five','Six','Seven',
 'License','Licence','Copyright','Readme','Json','Html','Http','Https','Url','Uri',
 'Jordan','Rash','Director','Tax','Transformation',
 'Automation','Partner','Manager','Senior','Associate',
 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday',
 'January','February','March','April','May','June','July','August','September',
 'October','November','December',
 'Startup','Users','Local','Roaming','Program','System','Temp','Desktop','Documents',
 'Downloads','Flow','Flows','Agent','Agents','Plugin','Plugins','Connector','Connectors',
 'Environment','Environments','Solution','Solutions','Workflow','Workflows',
 'Response','Request','Trigger','Triggers','Action','Actions','Definition',
 'Table','Tables','Row','Rows','Column','Columns','Cell','Cells','Index',
 'Memory','Lesson','Lessons','Digest','Gate','Gates','Check','Checks','Scan','Scans',
 'Build','Builds','Commit','Commits','Push','Pull','Branch','Main','Master','Repo',
 'Batch','Exec','Executor','Watchdog','Tunnel','Port','Ports','Host','Hosts',
 'Approved','Refused','Blocked','Allowed','Clean','Stale','Fresh','Live','Draft',
 'Yes','Fail','Pass','Warn','Skip','Stop','Start','End','Begin','Done','Never',
 'Attribution','Integrity','Guardrail','Guardrails','Contract','Scope','Surface',
 'Only','Once','Also','Just','Even','Same','Other','Another','First','Second','Last',
 'Before','After','Because','Since','While','Until','Unless','Rather','Instead',
 'Session','Sessions','Chat','User','Machine','Laptop','Browser','Page','Pages',
 'Name','Names','Value','Values','Text','Data','Config','Setup','Install','Version',
 'Return','Returns','Result','Results','Output','Input','Call','Calls','Exit','Code'
)

$counts = @{}
foreach ($f in $files) {
    $c = $null
    try { $c = Get-Content -Raw -ErrorAction Stop $f.FullName } catch { continue }
    if (-not $c) { continue }
    foreach ($m in [regex]::Matches($c, '\b([A-Z][a-z]{2,})(?:\s+([A-Z][a-z]{2,}))?\b')) {
        $w1 = $m.Groups[1].Value
        $w2 = $m.Groups[2].Value
        if ($stop -contains $w1) { continue }
        $key = if ($w2 -and -not ($stop -contains $w2)) { "$w1 $w2" } else { $w1 }
        if (-not $counts.ContainsKey($key)) { $counts[$key] = 0 }
        $counts[$key]++
    }
}

Write-Output ("scanned {0} text file(s) in the BUILT tree" -f $files.Count)
Write-Output ""
Write-Output "=== email addresses and external domains ==="
$mails = @{}
foreach ($f in $files) {
    $c = $null
    try { $c = Get-Content -Raw -ErrorAction Stop $f.FullName } catch { continue }
    if (-not $c) { continue }
    foreach ($m in [regex]::Matches($c, '[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')) {
        $v = $m.Value
        if (-not $mails.ContainsKey($v)) { $mails[$v] = 0 }
        $mails[$v]++
    }
}
if ($mails.Count) {
    $mails.GetEnumerator() | Sort-Object Value -Descending |
        ForEach-Object { Write-Output ("  {0,4}x  {1}" -f $_.Value, $_.Key) }
} else { Write-Output "  none" }

Write-Output ""
Write-Output "=== name-shaped tokens that are NOT known technology terms ==="
Write-Output "    Most will be ordinary prose. Anything that is a company or a"
Write-Output "    person outside the firm is what matters."
Write-Output ""

$residue = $counts.GetEnumerator() | Sort-Object Value -Descending
$shown = 0
foreach ($r in $residue) {
    if ($shown -ge 50) { break }
    Write-Output ("  {0,4}x  {1}" -f $r.Value, $r.Key)
    $shown++
}
Write-Output ""
Write-Output ("  {0} distinct token(s); showing the {1} most frequent" -f $residue.Count, $shown)
exit 0
