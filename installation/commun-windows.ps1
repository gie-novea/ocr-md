# Fonctions communes aux scripts Windows d'ocr-md (EX-69, EX-72, EX-73).
# Tout s'installe dans le profil de l'utilisateur, sans droits d'administrateur (EX-02).

# Source de distribution (EX-69) : archive de la version publiée sur GitHub (étiquette v1.0.0),
# installée par uv sans Git (décision du commanditaire du 27/11/2026).
# Elle peut être remplacée par le paramètre -Source (chemin d'un dossier ou d'un paquet
# « wheel », ou autre adresse) ou par la variable d'environnement OCR_MD_SOURCE.
$SourceParDefaut = "https://github.com/gie-novea/ocr-md/archive/refs/tags/v1.0.0.zip"
$VersionPython = "3.12"

# « Continue » : sous Windows PowerShell 5.1, avec « Stop », un message de uv sur la sortie
# d'erreur deviendrait une erreur bloquante ; chaque étape vérifie donc son résultat.
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Get-SourceOcrMd([string]$Source) {
    if ($Source) { return $Source }
    if ($env:OCR_MD_SOURCE) { return $env:OCR_MD_SOURCE }
    return $SourceParDefaut
}

function Write-Etape([int]$Numero, [string]$Texte) {
    Write-Host ""
    Write-Host "[$Numero] $Texte" -ForegroundColor Cyan
}

function Get-CheminUv {
    $local = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path $local) { return $local }
    $commande = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($commande) { return $commande.Source }
    return $null
}

function Install-Uv {
    $uv = Get-CheminUv
    if ($uv) {
        Write-Host "uv est déjà installé : $uv"
        return $uv
    }
    Write-Host "Installation de uv dans le profil (astral.sh)..."
    $script = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing -ErrorAction Stop
    Invoke-Expression $script
    $uv = Get-CheminUv
    if (-not $uv) { throw "uv n'a pas été installé (vérifier l'accès à astral.sh et à GitHub)" }
    Write-Host "uv installé : $uv"
    return $uv
}

function Install-PythonOcrMd([string]$Uv) {
    # uv peut afficher une erreur alors que l'installation a réussi (observation du jalon 0) :
    # le résultat est vérifié par « uv python find » plutôt que par le seul code de retour.
    & $Uv python install $VersionPython
    $codeInstallation = $LASTEXITCODE
    $python = & $Uv python find $VersionPython 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $python) {
        throw "Python $VersionPython n'a pas pu être installé par uv (code $codeInstallation)"
    }
    if ($codeInstallation -ne 0) {
        Write-Host "uv a signalé une erreur, mais Python $VersionPython est bien installé : $python"
    } else {
        Write-Host "Python $VersionPython disponible : $python"
    }
}

function Get-CheminOcrMd([string]$Uv) {
    $bin = & $Uv tool dir --bin 2>$null
    if ($LASTEXITCODE -eq 0 -and $bin) {
        $chemin = Join-Path ($bin | Select-Object -First 1).Trim() "ocr-md.exe"
        if (Test-Path $chemin) { return $chemin }
    }
    $commande = Get-Command ocr-md.exe -ErrorAction SilentlyContinue
    if ($commande) { return $commande.Source }
    return $null
}

function Get-VersionOcrMd([string]$OcrMd) {
    if (-not $OcrMd -or -not (Test-Path $OcrMd)) { return $null }
    $sortie = & $OcrMd --version 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $sortie) { return $null }
    return ($sortie | Select-Object -First 1).Trim()
}

function Invoke-Verification([string]$OcrMd) {
    & $OcrMd verifier
    if ($LASTEXITCODE -eq 3) {
        Write-Host ""
        Write-Host "Un prérequis manque (voir les lignes [X] ci-dessus). L'outil est installé ; les fichiers qui n'ont pas besoin de ce prérequis restent traités." -ForegroundColor Yellow
    }
}

function Confirm-Choix([string]$Question, [string]$Reponse) {
    # $Reponse : « oui » ou « non » pour un lancement sans question (essais), vide pour demander.
    if ($Reponse -match '^\s*(oui|o)\s*$') { return $true }
    if ($Reponse -match '^\s*(non|n)\s*$') { return $false }
    $r = Read-Host "$Question (o/n)"
    return $r -match '^\s*[oOyY]'
}

function Wait-Fin {
    if (-not $env:OCR_MD_SANS_PAUSE) {
        Write-Host ""
        Read-Host "Appuyer sur Entrée pour fermer"
    }
}
