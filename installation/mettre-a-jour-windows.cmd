@echo off
rem Lanceur par double-clic : appelle mettre-a-jour-windows.ps1 avec -ExecutionPolicy Bypass pour ce seul
rem processus (EX-69). Aucun droit d'administrateur n'est demandé.
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0mettre-a-jour-windows.ps1" %*
exit /b %ERRORLEVEL%
