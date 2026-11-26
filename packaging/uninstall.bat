@echo off
rem LiveWikiMe uninstaller for Windows (double-click). Keep this file ASCII only.
setlocal
set "PYEXE=%USERPROFILE%\LiveWikiMe\.venv\Scripts\python.exe"
set "PYARGS="
if not exist "%PYEXE%" (set "PYEXE=py" & set "PYARGS=-3")
"%PYEXE%" %PYARGS% -X utf8 "%~dp0uninstall_win.py"
echo.
pause
