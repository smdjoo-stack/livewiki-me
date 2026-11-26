@echo off
rem LiveWikiMe installer for Windows (double-click). Keep this file ASCII only.
setlocal
cd /d "%~dp0"
set "PYEXE="
set "PYARGS="

py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul && (set "PYEXE=py" & set "PYARGS=-3")
if not defined PYEXE python -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE for %%V in (314 313 312 311 310) do if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
if not defined PYEXE goto nopython

"%PYEXE%" %PYARGS% -X utf8 "%~dp0install_win.py"
goto end

:nopython
echo.
echo [Python 3.9 or newer was not found]
echo Trying to install Python 3.12 with winget...
echo.
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -X utf8 "%~dp0install_win.py"
  goto end
)
echo.
echo Could not install Python automatically.
echo 1. Install Python from https://www.python.org/downloads/
echo    (check "Add python.exe to PATH" on the first screen)
echo 2. Run install.bat again.
start "" "https://www.python.org/downloads/"

:end
echo.
pause
