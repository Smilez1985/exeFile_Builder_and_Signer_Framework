@echo off
:: Wrapper Script um die PowerShell Policy zu umgehen
cd /d "%~dp0"
echo Starte ExeBuilder Launcher...
powershell -NoProfile -ExecutionPolicy Bypass -File "launcher.ps1"
