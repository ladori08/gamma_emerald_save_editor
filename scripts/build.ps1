$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Create it and install requirements-dev.txt first."
}
Push-Location $projectRoot
try {
    # Capture the local runtime key before PyInstaller replaces dist. This keeps
    # repeat local builds directly runnable without publishing the key.
    $runtimeKey = $env:GAMMA_EMERALD_SAVE_KEY_HEX
    if (-not $runtimeKey) {
        $keyCandidates = @(
            (Join-Path $projectRoot "dist\GammaEmeraldSaveEditor\save_key.hex"),
            (Join-Path $projectRoot "dist\save_key.hex"),
            (Join-Path $projectRoot "save_key.hex"),
            (Join-Path $env:LOCALAPPDATA "GammaEmeraldSaveEditor\save_key.hex")
        )
        foreach ($candidate in $keyCandidates) {
            if (Test-Path -LiteralPath $candidate) {
                $runtimeKey = Get-Content -LiteralPath $candidate -Raw
                break
            }
        }
    }
    if ($runtimeKey) {
        $runtimeKey = ($runtimeKey -replace '\s', '')
        if ($runtimeKey -notmatch '^[0-9a-fA-F]{64}$') {
            throw "GAMMA_EMERALD_SAVE_KEY_HEX/save_key.hex must contain exactly 64 hexadecimal characters."
        }
    }

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
    $buildTemp = Join-Path $projectRoot ".build_temp"
    New-Item -ItemType Directory -Path $buildTemp -Force | Out-Null
    $env:TEMP = $buildTemp
    $env:TMP = $buildTemp
    & $python -B -m pytest -q --basetemp (Join-Path $buildTemp "pytest")
    if ($LASTEXITCODE -ne 0) {
        throw "Automated tests failed; build stopped."
    }
    & $python -m PyInstaller --noconfirm --clean --onedir --windowed --name GammaEmeraldSaveEditor `
        --paths src packaging\gui_launcher.py
    if ($LASTEXITCODE -ne 0) {
        throw "GUI build failed."
    }
    & $python -m PyInstaller --noconfirm --clean --onefile --console --name gamma-save `
        --paths src packaging\cli_launcher.py
    if ($LASTEXITCODE -ne 0) {
        throw "CLI build failed."
    }
    if ($runtimeKey) {
        [IO.File]::WriteAllText(
            (Join-Path $projectRoot "dist\GammaEmeraldSaveEditor\save_key.hex"),
            $runtimeKey,
            [Text.Encoding]::ASCII
        )
        [IO.File]::WriteAllText(
            (Join-Path $projectRoot "dist\save_key.hex"),
            $runtimeKey,
            [Text.Encoding]::ASCII
        )
    }

    $workspaceRoot = Split-Path -Parent $projectRoot
    $launcherTemplate = Join-Path $projectRoot "packaging\root_launcher.cmd"
    $launcherTarget = Join-Path $workspaceRoot "GammaEmeraldSaveEditor.cmd"
    Copy-Item -LiteralPath $launcherTemplate -Destination $launcherTarget -Force
    Write-Output "Root launcher refreshed: $launcherTarget"
} finally {
    Pop-Location
}
