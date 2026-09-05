@echo off
setlocal

set "EDITOR_EXE=%~dp0gamma_emerald_save_editor\dist\GammaEmeraldSaveEditor\GammaEmeraldSaveEditor.exe"

if not exist "%EDITOR_EXE%" (
    echo Gamma Emerald Save Editor has not been built yet.
    echo Expected: "%EDITOR_EXE%"
    echo Run gamma_emerald_save_editor\scripts\build.ps1 first.
    pause
    exit /b 1
)

start "" "%EDITOR_EXE%"
exit /b %ERRORLEVEL%
