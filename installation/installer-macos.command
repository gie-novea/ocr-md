#!/bin/bash
# Installation d'ocr-md sous macOS (EX-69) : idempotente, dans le profil, sans droits
# d'administrateur. Lancer par double-clic. Argument facultatif : source de distribution.
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/commun-macos.sh"
SOURCE="$(source_ocr_md "${1:-}")"
ETAPE=0

installer() {
    echo "Installation d'ocr-md (source : $SOURCE)"
    etape 1 "Installation de uv" && installer_uv || return 1
    etape 2 "Installation de Python $VERSION_PYTHON géré par uv" && installer_python || return 1
    etape 3 "Installation de l'outil"
    "$UV" tool install --python "$VERSION_PYTHON" "$SOURCE" || { echo "uv tool install a échoué"; return 1; }
    OCRMD="$(chemin_ocr_md)"
    [ -n "$OCRMD" ] || { echo "la commande ocr-md est introuvable après l'installation"; return 1; }
    etape 4 "Création des trois Actions rapides du Finder"
    "$OCRMD" raccourcis --creer || { echo "création des Actions rapides impossible"; return 1; }
    etape 5 "Vérification des prérequis"
    verification "$OCRMD"
    printf '\nInstallation terminée : %s. Clic droit sur un fichier ou un dossier dans le Finder, puis « Actions rapides », puis « OCR - ... ».\n' "$(version_ocr_md "$OCRMD")"
}

if installer; then CODE=0; else
    printf '\nÉchec de l'"'"'installation à l'"'"'étape %s.\n' "$ETAPE"
    CODE=1
fi
attendre_fin
exit $CODE
