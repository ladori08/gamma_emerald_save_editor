$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Create it and install requirements-dev.txt first."
}
Push-Location $projectRoot
try {
    # Some managed Windows accounts cannot initialize Tcl from another user's
    # Python directory. Stage the installed Tcl/Tk library inside the project
    # so PyInstaller can inspect and bundle it reliably.
    $basePrefix = (& $python -c "import sys; print(sys.base_prefix)").Trim()
    $tclSource = Join-Path $basePrefix "tcl"
    $tclStage = Join-Path $projectRoot ".build_tcl"
    New-Item -ItemType Directory -Path $tclStage -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $tclSource "tcl8.6") -Destination $tclStage -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $tclSource "tk8.6") -Destination $tclStage -Recurse -Force
    $env:TCL_LIBRARY = Join-Path $tclStage "tcl8.6"
    $env:TK_LIBRARY = Join-Path $tclStage "tk8.6"
    & $python -B -m pytest -q
    & $python -m PyInstaller --noconfirm --clean --onedir --windowed --name GammaEmeraldSaveEditor `
        --paths src packaging\gui_launcher.py
    & $python -m PyInstaller --noconfirm --clean --onefile --console --name gamma-save `
        --paths src packaging\cli_launcher.py
} finally {
    Pop-Location
}
