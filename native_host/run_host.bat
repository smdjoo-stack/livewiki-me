@echo off
rem Chrome/Edge/Brave start this file (Windows). Keep this file ASCII only.
set "PATH=%USERPROFILE%\.local\bin;%APPDATA%\npm;%PATH%"
"%~dp0..\.venv\Scripts\python.exe" -I -X utf8 "%~dp0livewiki_host.py" %* 2>>"%~dp0host.log"
