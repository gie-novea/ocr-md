@echo off
rem Lanceur par double-clic : appelle desinstaller-windows.ps1 avec -ExecutionPolicy Bypass pour ce seul
rem processus (EX-69). Aucun droit d'administrateur n'est demandé.
chcp 65001 >nul
rem Chemins de modules de Windows PowerShell par défaut : lancé depuis PowerShell 7, le script
rem hériterait des siens, que Windows PowerShell 5.1 ne sait pas charger (Get-ExecutionPolicy).
set "PSModulePath="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0desinstaller-windows.ps1" %*
exit /b %ERRORLEVEL%
