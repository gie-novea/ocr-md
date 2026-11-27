# Installation d'ocr-md sous Windows (EX-69) : idempotente, dans le profil, sans droits
# d'administrateur. Lancer par double-clic sur installer-windows.cmd.
param([string]$Source = "")

. (Join-Path $PSScriptRoot "commun-windows.ps1")
$source = Get-SourceOcrMd $Source
$etape = 0
try {
    Write-Host "Installation d'ocr-md (source : $source)"
    $etape = 1; Write-Etape 1 "Installation de uv"
    $uv = Install-Uv
    $etape = 2; Write-Etape 2 "Installation de Python $VersionPython géré par uv"
    Install-PythonOcrMd $uv
    $etape = 3; Write-Etape 3 "Installation de l'outil"
    & $uv tool install --python $VersionPython $source
    if ($LASTEXITCODE -ne 0) { throw "uv tool install a échoué (code $LASTEXITCODE)" }
    $ocrmd = Get-CheminOcrMd $uv
    if (-not $ocrmd) { throw "la commande ocr-md est introuvable après l'installation" }
    $etape = 4; Write-Etape 4 "Création des trois raccourcis « Envoyer vers »"
    & $ocrmd raccourcis --creer
    if ($LASTEXITCODE -ne 0) { throw "création des raccourcis impossible (code $LASTEXITCODE)" }
    $etape = 5; Write-Etape 5 "Vérification des prérequis"
    Invoke-Verification $ocrmd
    Write-Host ""
    Write-Host "Installation terminée : $(Get-VersionOcrMd $ocrmd). Clic droit sur un fichier ou un dossier, puis « Envoyer vers » (sous Windows 11 : « Afficher d'autres options »), puis « OCR - ... »." -ForegroundColor Green
    $code = 0
} catch {
    Write-Host ""
    Write-Host "Échec de l'installation à l'étape $etape : $($_.Exception.Message)" -ForegroundColor Red
    $code = 1
}
Wait-Fin
exit $code
