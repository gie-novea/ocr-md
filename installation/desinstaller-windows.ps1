# Désinstallation d'ocr-md sous Windows (EX-73) : raccourcis retirés, outil désinstallé,
# dossier temporaire supprimé ; configuration supprimée après confirmation ; désinstallation de
# uv et de ses Pythons proposée sans être imposée. Les dossiers _OCR ne sont jamais touchés.
# -SupprimerConfiguration et -DesinstallerUv (« oui » ou « non ») évitent les questions (essais).
param([string]$SupprimerConfiguration = "", [string]$DesinstallerUv = "")

. (Join-Path $PSScriptRoot "commun-windows.ps1")
$etape = 0
try {
    $uv = Get-CheminUv
    $ocrmd = if ($uv) { Get-CheminOcrMd $uv } else { $null }
    $etape = 1; Write-Etape 1 "Retrait des raccourcis"
    if ($ocrmd) {
        & $ocrmd raccourcis --supprimer
    } else {
        $sendto = Join-Path $env:APPDATA "Microsoft\Windows\SendTo"
        foreach ($nom in "OCR - Rendre lisible (PDF).lnk", "OCR - Convertir en Markdown.lnk", "OCR - Les deux.lnk") {
            Remove-Item -LiteralPath (Join-Path $sendto $nom) -ErrorAction SilentlyContinue
        }
        Write-Host "Raccourcis retirés (outil absent)."
    }
    $etape = 2; Write-Etape 2 "Désinstallation de l'outil"
    if ($uv) {
        & $uv tool uninstall ocr-md
        if ($LASTEXITCODE -ne 0) { Write-Host "ocr-md n'était pas installé par uv." }
    }
    $etape = 3; Write-Etape 3 "Suppression du dossier temporaire"
    Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA "ocr-md") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Dossier temporaire supprimé."
    $etape = 4; Write-Etape 4 "Configuration"
    $configuration = Join-Path $env:APPDATA "ocr-md"
    if (Test-Path $configuration) {
        if (Confirm-Choix "Supprimer aussi le fichier de configuration ($configuration) ?" $SupprimerConfiguration) {
            Remove-Item -LiteralPath $configuration -Recurse -Force -ErrorAction Stop
            Write-Host "Configuration supprimée."
        } else {
            Write-Host "Configuration conservée : $configuration"
        }
    }
    $etape = 5; Write-Etape 5 "uv et ses Pythons"
    if ($uv -and (Confirm-Choix "Désinstaller aussi uv et ses Pythons ? D'autres outils peuvent en dépendre." $DesinstallerUv)) {
        & $uv cache clean
        $pythons = & $uv python dir
        $outils = & $uv tool dir
        Remove-Item -LiteralPath $pythons, $outils -Recurse -Force -ErrorAction SilentlyContinue
        foreach ($nom in "uv.exe", "uvx.exe", "uvw.exe") {
            Remove-Item -LiteralPath (Join-Path (Split-Path $uv) $nom) -ErrorAction SilentlyContinue
        }
        Write-Host "uv et ses Pythons désinstallés."
    } else {
        Write-Host "uv conservé."
    }
    Write-Host ""
    Write-Host "Désinstallation terminée. Les dossiers _OCR produits n'ont pas été touchés." -ForegroundColor Green
    $code = 0
} catch {
    Write-Host ""
    Write-Host "Échec de la désinstallation à l'étape $etape : $($_.Exception.Message)" -ForegroundColor Red
    $code = 1
}
Wait-Fin
exit $code
