# Mise à jour d'ocr-md sous Windows (EX-72) : réinstalle la dernière version depuis la source
# de distribution, recrée les raccourcis, relance la vérification, affiche l'ancienne et la
# nouvelle version. Le fichier de configuration de l'utilisateur est conservé.
param([string]$Source = "")

. (Join-Path $PSScriptRoot "commun-windows.ps1")
$source = Get-SourceOcrMd $Source
$etape = 0
try {
    $etape = 1; Write-Etape 1 "Recherche de l'installation"
    $uv = Get-CheminUv
    if (-not $uv) { throw "uv est introuvable : lancer d'abord installer-windows.cmd" }
    $ancienne = Get-VersionOcrMd (Get-CheminOcrMd $uv)
    if (-not $ancienne) { throw "ocr-md n'est pas installé : lancer d'abord installer-windows.cmd" }
    Write-Host "Version installée : $ancienne"
    $etape = 2; Write-Etape 2 "Installation de la dernière version (source : $source)"
    Install-PythonOcrMd $uv
    & $uv tool install --force --reinstall --python $VersionPython $source
    if ($LASTEXITCODE -ne 0) { throw "uv tool install a échoué (code $LASTEXITCODE)" }
    $ocrmd = Get-CheminOcrMd $uv
    $etape = 3; Write-Etape 3 "Recréation des raccourcis"
    & $ocrmd raccourcis --creer
    if ($LASTEXITCODE -ne 0) { throw "création des raccourcis impossible (code $LASTEXITCODE)" }
    $etape = 4; Write-Etape 4 "Vérification des prérequis"
    Invoke-Verification $ocrmd
    Write-Host ""
    Write-Host "Mise à jour terminée : $ancienne, puis $(Get-VersionOcrMd $ocrmd)." -ForegroundColor Green
    $code = 0
} catch {
    Write-Host ""
    Write-Host "Échec de la mise à jour à l'étape $etape : $($_.Exception.Message)" -ForegroundColor Red
    $code = 1
}
Wait-Fin
exit $code
