# install.ps1 - set up Ask My Files in this folder.
#   .\install.ps1              create .venv, install packages, check Ollama and the models
#   .\install.ps1 -ChecksOnly  only check Ollama and the models
param([switch]$ChecksOnly)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$script:failed = $false

function Ok($message)   { Write-Output "[OK] $message" }
function Fail($message) { Write-Output "[FAIL] $message"; $script:failed = $true }

function Setting($name, $default) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrEmpty($value)) { return $default }
    return $value
}

# --- Python environment and packages ---
if (-not $ChecksOnly) {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
    }
    if (-not (Test-Path $venvPython)) {
        Fail "Could not create .venv. Install Python 3.11 or newer from https://www.python.org and run this script again."
    } else {
        & $venvPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
        if ($LASTEXITCODE -ne 0) {
            Fail "The Python in .venv is older than 3.11. Delete the .venv folder, install Python 3.11 or newer, and run this script again."
        } else {
            Ok "Python environment .venv is ready."
            & $venvPython -m pip install --quiet --disable-pip-version-check -r requirements.txt
            if ($LASTEXITCODE -eq 0) { & $venvPython -m pip install --quiet --disable-pip-version-check -e . }
            if ($LASTEXITCODE -eq 0) { Ok "Packages are installed." }
            else { Fail "Package installation failed. Check your internet connection and the pip output above." }
        }
    }
}

# --- Ollama and models ---
$url = (Setting "ASKFILES_OLLAMA_URL" "http://localhost:11434").TrimEnd("/")
$models = @((Setting "ASKFILES_CHAT_MODEL" "qwen2.5:7b"), (Setting "ASKFILES_EMBED_MODEL" "nomic-embed-text"))
$tags = $null
try {
    $tags = Invoke-RestMethod -Uri "$url/api/tags" -TimeoutSec 10
    Ok "Ollama answers on $url."
} catch {
    Fail "Ollama does not answer on $url. Install Ollama from https://ollama.com, start it, and run this script again."
}
if ($tags) {
    $installed = @($tags.models | ForEach-Object { $_.name })
    foreach ($model in $models) {
        if (($installed -contains $model) -or ($installed -contains "${model}:latest")) {
            Ok "Model '$model' is installed."
        } else {
            Fail "Model '$model' is not installed. Run: ollama pull $model"
        }
    }
} else {
    foreach ($model in $models) { Write-Output "[SKIP] Model '$model' was not checked because Ollama does not answer." }
}

if ($script:failed) {
    Write-Output ""
    Write-Output "Setup is not complete. Fix the [FAIL] lines above and run .\install.ps1 again."
    exit 1
}
Write-Output ""
Write-Output "Setup is complete. Index a folder, then start the web page:"
Write-Output "  .\.venv\Scripts\python.exe -m askfiles index C:\path\to\documents"
Write-Output "  .\run.ps1"
exit 0
