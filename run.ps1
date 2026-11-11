# run.ps1 - start the Ask My Files web page on http://127.0.0.1:5000
Set-Location $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Output "The Python environment .venv is missing. Run .\install.ps1 first."
    exit 1
}
Write-Output "Ask My Files runs on http://127.0.0.1:5000 - press Ctrl+C to stop."
& $venvPython -m askfiles.web
exit $LASTEXITCODE
