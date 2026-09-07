$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\YOURUSER\Documents\COPILOT_COWORK'

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { Write-Output 'COWORK_RESULT: FAIL - git not installed'; exit 1 }
Write-Output "git: $($git.Source)"
Write-Output (git --version)

if (Test-Path "$repo\.git") { Write-Output 'COWORK_RESULT: FAIL - repo already exists'; exit 1 }

@'
# Build / dependency
node_modules/
package-lock.json

# Generated output and logs
Outputs/
autorun/logs/
autorun/queue/
CommandJobs/Logs/
playwright-output/
*.log

# Hand-made backups - git replaces these
*.bak
*.backup
*-backup
*.pre-*

# Archives and binaries
*.zip

# Anything credential-shaped - NEVER commit
*.env
*secret*
*credential*
*token*
*.key
*.pem
'@ | Set-Content -Path "$repo\.gitignore" -Encoding UTF8

Set-Location $repo
git init -q
git config user.name  'Jordan Rash'
git config user.email 'you@example.com'
git add -A
$staged = @(git diff --cached --name-only).Count
if ($staged -gt 400) { Write-Output "COWORK_RESULT: FAIL - $staged files staged, gitignore likely wrong"; exit 1 }
git commit -q -m 'Initial commit: Cowork local bridge configuration baseline'

Write-Output "files committed: $staged"
Write-Output (git log --oneline -1)
Write-Output "COWORK_RESULT: PASS"
exit 0
