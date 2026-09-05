$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Create it and install requirements-dev.txt first."
}
$env:PYTHONPATH = Join-Path $projectRoot "src"
& $python -B -m pytest -q

