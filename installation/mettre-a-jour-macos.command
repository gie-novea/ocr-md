#!/bin/bash
# Mise à jour d'ocr-md sous macOS (EX-72) : réinstalle la dernière version depuis la source de
# distribution, recrée les Actions rapides, relance la vérification, affiche l'ancienne et la
# nouvelle version. Le fichier de configuration de l'utilisateur est conservé.
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/commun-macos.sh"
SOURCE="$(source_ocr_md "${1:-}")"
ETAPE=0

mettre_a_jour() {
    etape 1 "Recherche de l'installation"
    UV="$(chemin_uv)"
    [ -n "$UV" ] || { echo "uv est introuvable : lancer d'abord installer-macos.command"; return 1; }
    ANCIENNE="$(version_ocr_md "$(chemin_ocr_md)")"
    [ -n "$ANCIENNE" ] || { echo "ocr-md n'est pas installé : lancer d'abord installer-macos.command"; return 1; }
    echo "Version installée : $ANCIENNE"
    etape 2 "Installation de la dernière version (source : $SOURCE)"
    installer_python || return 1
    "$UV" tool install --force --reinstall --python "$VERSION_PYTHON" "$SOURCE" || { echo "uv tool install a échoué"; return 1; }
    OCRMD="$(chemin_ocr_md)"
    etape 3 "Recréation des Actions rapides"
    "$OCRMD" raccourcis --creer || { echo "création des Actions rapides impossible"; return 1; }
    etape 4 "Vérification des prérequis"
    verification "$OCRMD"
    printf '\nMise à jour terminée : %s, puis %s.\n' "$ANCIENNE" "$(version_ocr_md "$OCRMD")"
}

if mettre_a_jour; then CODE=0; else
    printf '\nÉchec de la mise à jour à l'"'"'étape %s.\n' "$ETAPE"
    CODE=1
fi
attendre_fin
exit $CODE
