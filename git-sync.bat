@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0git-sync.ps1" %*
endlocal
