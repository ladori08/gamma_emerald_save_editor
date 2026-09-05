[CmdletBinding()]
param(
    [string]$SaveFolder = (Join-Path $env:LOCALAPPDATA "PokemonEmerald\Saved\.ged"),
    [ValidateRange(1, 50)]
    [int]$RecentBackups = 8,
    [ValidateRange(1, 20)]
    [int]$RecentCrashes = 3
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$cli = Join-Path $projectRoot "dist\gamma-save.exe"
$savedRoot = Split-Path -Parent $SaveFolder

Write-Output "Gamma Emerald read-only save diagnostic"
Write-Output "Project: $projectRoot"
Write-Output "Save folder: $SaveFolder"
Write-Output "This script does not create, edit, restore, move, or delete save files."

if (-not (Test-Path -LiteralPath $SaveFolder -PathType Container)) {
    throw "Save folder does not exist: $SaveFolder"
}
if (-not (Test-Path -LiteralPath $cli -PathType Leaf)) {
    throw "Packaged CLI is missing. Build the project first: $cli"
}

Write-Output ""
Write-Output "[Processes]"
$processes = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match "PokemonEmerald|GammaEmeraldSaveEditor|gamma-save"
}
if ($processes) {
    $processes | ForEach-Object {
        Write-Output ("RUNNING pid={0} name={1} started={2:yyyy-MM-dd HH:mm:ss}" -f `
            $_.Id, $_.ProcessName, $_.StartTime)
    }
    Write-Output "WARNING: files can change while the game/editor is running. Diagnose now, but close both before recovery."
} else {
    Write-Output "No game/editor process detected."
}

Write-Output ""
Write-Output "[Live slots]"
$liveFiles = Get-ChildItem -LiteralPath $SaveFolder -Force -File |
    Where-Object { $_.Extension -eq ".dat" } |
    Sort-Object LastWriteTime -Descending

if (-not $liveFiles) {
    Write-Output "No live .dat slots found."
}

$invalidCount = 0
foreach ($file in $liveFiles) {
    $summaryText = (& $cli summary $file.FullName 2>&1) -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0) {
        $invalidCount += 1
        Write-Output ("INVALID name={0} bytes={1} modified={2:yyyy-MM-dd HH:mm:ss}" -f `
            $file.Name, $file.Length, $file.LastWriteTime)
        Write-Output $summaryText
        continue
    }
    $summary = $summaryText | ConvertFrom-Json
    Write-Output ("OK slot={0} class={1} bytes={2} gvas={3} properties={4} modified={5:yyyy-MM-dd HH:mm:ss} sha256={6}" -f `
        $summary.slot_name, $summary.save_game_class, $file.Length, $summary.gvas_size,
        $summary.parsed_property_count, $file.LastWriteTime, $summary.sha256)
    if ($summary.property_parser_note) {
        Write-Output ("  PARSER NOTE: {0}" -f $summary.property_parser_note)
    }
}

Write-Output ""
Write-Output "[Recent automatic backups]"
$backups = Get-ChildItem -LiteralPath $SaveFolder -Force -File |
    Where-Object { $_.Name -like "*.preedit-*.bak" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First $RecentBackups
if (-not $backups) {
    Write-Output "No automatic backups found."
} else {
    foreach ($file in $backups) {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        Write-Output ("name={0} bytes={1} modified={2:yyyy-MM-dd HH:mm:ss} sha256={3}" -f `
            $file.Name, $file.Length, $file.LastWriteTime, $hash)
    }
}

Write-Output ""
Write-Output "[Recent crashes]"
$crashRoot = Join-Path $savedRoot "Crashes"
$crashes = @()
if (Test-Path -LiteralPath $crashRoot -PathType Container) {
    $crashes = Get-ChildItem -LiteralPath $crashRoot -Recurse -Force -File -Filter "CrashContext.runtime-xml" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First $RecentCrashes
}
if (-not $crashes) {
    Write-Output "No CrashContext.runtime-xml files found."
} else {
    foreach ($file in $crashes) {
        try {
            [xml]$document = Get-Content -LiteralPath $file.FullName -Raw
            $errorNode = $document.SelectSingleNode("//ErrorMessage")
            $secondsNode = $document.SelectSingleNode("//SecondsSinceStart")
            $hashNode = $document.SelectSingleNode("//PCallStackHash")
            Write-Output ("modified={0:yyyy-MM-dd HH:mm:ss} seconds={1} stack_hash={2}" -f `
                $file.LastWriteTime, $secondsNode.InnerText, $hashNode.InnerText)
            Write-Output ("  {0}" -f $errorNode.InnerText)
        } catch {
            Write-Output ("Could not parse {0}: {1}" -f $file.FullName, $_.Exception.Message)
        }
    }
}

Write-Output ""
Write-Output "[Latest game diagnostics]"
$gameLog = Join-Path $savedRoot "Logs\GammaEmerald-Diagnostics.log"
if (Test-Path -LiteralPath $gameLog -PathType Leaf) {
    Get-Content -LiteralPath $gameLog -Tail 30
} else {
    Write-Output "No GammaEmerald-Diagnostics.log found."
}

Write-Output ""
Write-Output "[Interpretation]"
if ($invalidCount -gt 0) {
    Write-Output "One or more live slots failed container/parser validation. Do not launch or overwrite them; preserve the whole .ged folder."
} else {
    Write-Output "Every detected live slot passed structural checks. This does NOT prove runtime validity."
}
Write-Output "Compare slot timestamps as a set. Story, Quest, Berry, and Options written in different sessions may produce mixed progression."
Write-Output "For Unknown species or blank moves, compare a game-authored pre-edit backup with the editor-authored live file at byte level."
Write-Output "Never restore while PokemonEmerald-Win64-Shipping.exe or the editor is running."
