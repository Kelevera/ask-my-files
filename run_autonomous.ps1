# run_autonomous.ps1
$ErrorActionPreference = "Continue"
$projectDir   = "C:\Projects\ask-my-files"
$model        = "claude-fable-5-2"   # change to "opus" if this model is not available for you
$maxSessions  = 200
$pauseSeconds = 600                  # wait 10 minutes between sessions

Set-Location $projectDir

if (-not (Test-Path ".git")) {
    git init | Out-Null
    git add -A
    git commit -m "init" | Out-Null
}

for ($i = 1; $i -le $maxSessions; $i++) {
    if (Test-Path "STATUS.md") {
        $state = Get-Content "STATUS.md" -TotalCount 1
        if ($state -match "STATE: DONE")    { Write-Host "FINISHED: DONE";   break }
        if ($state -match "STATE: BLOCKED") { Write-Host "STOPPED: BLOCKED"; break }
    }

    Write-Host "Session $i starting $(Get-Date)"
    claude -p "Continue the project. Follow CLAUDE.md exactly. Start by reading STATUS.md." `
        --model $model `
        --dangerously-skip-permissions 2>&1 | Tee-Object -FilePath "run.log" -Append
    Write-Host "Session $i ended $(Get-Date). Waiting $pauseSeconds seconds."
    Start-Sleep -Seconds $pauseSeconds
}

Write-Host "Loop finished. Read STATUS.md."