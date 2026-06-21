@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m PyInstaller --version >nul 2>&1
    if not errorlevel 1 (
        ".venv\Scripts\python.exe" -m PyInstaller gear.spec
        goto :end
    )
)

where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m PyInstaller --version >nul 2>&1
    if not errorlevel 1 (
        py -3 -m PyInstaller gear.spec
        goto :end
    )
)

python -m PyInstaller --version >nul 2>&1
if not errorlevel 1 (
    python -m PyInstaller gear.spec
    goto :end
)

echo PyInstaller is not available in .venv, py -3, or python.
exit /b 1

:end
endlocal