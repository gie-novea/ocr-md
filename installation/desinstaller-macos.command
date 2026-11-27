#!/bin/bash
# Désinstallation d'ocr-md sous macOS (EX-73) : Actions rapides retirées, outil désinstallé,
# dossier temporaire supprimé ; configuration supprimée après confirmation ; désinstallation de
# uv et de ses Pythons proposée sans être imposée. Les dossiers _OCR ne sont jamais touchés.
# Arguments facultatifs (essais) : réponse pour la configuration, puis pour uv (« oui » ou « non »).
ICI="$(cd "$(dirname "$0")" && pwd)"
. "$ICI/commun-macos.sh"
REPONSE_CONFIGURATION="${1:-}"
REPONSE_UV="${2:-}"
ETAPE=0

desinstaller() {
    UV="$(chemin_uv)"
    OCRMD=""
    [ -n "$UV" ] && OCRMD="$(chemin_ocr_md)"
    etape 1 "Retrait des Actions rapides"
    if [ -n "$OCRMD" ]; then
        "$OCRMD" raccourcis --supprimer
    else
        for nom in "OCR - Rendre lisible (PDF)" "OCR - Convertir en Markdown" "OCR - Les deux"; do
            rm -rf "$HOME/Library/Services/$nom.workflow"
        done
        echo "Actions rapides retirées (outil absent)."
    fi
    etape 2 "Désinstallation de l'outil"
    if [ -n "$UV" ]; then
        "$UV" tool uninstall ocr-md || echo "ocr-md n'était pas installé par uv."
    fi
    etape 3 "Suppression du dossier temporaire"
    rm -rf "$HOME/Library/Caches/ocr-md"
    echo "Dossier temporaire supprimé."
    etape 4 "Configuration"
    CONFIGURATION="$HOME/Library/Application Support/ocr-md"
    if [ -d "$CONFIGURATION" ]; then
        if confirmer "Supprimer aussi le fichier de configuration ($CONFIGURATION) ?" "$REPONSE_CONFIGURATION"; then
            rm -rf "$CONFIGURATION" && echo "Configuration supprimée."
        else
            echo "Configuration conservée : $CONFIGURATION"
        fi
    fi
    etape 5 "uv et ses Pythons"
    if [ -n "$UV" ] && confirmer "Désinstaller aussi uv et ses Pythons ? D'autres outils peuvent en dépendre." "$REPONSE_UV"; then
        "$UV" cache clean
        rm -rf "$("$UV" python dir)" "$("$UV" tool dir)"
        rm -f "$(dirname "$UV")/uv" "$(dirname "$UV")/uvx"
        echo "uv et ses Pythons désinstallés."
    else
        echo "uv conservé."
    fi
    printf '\nDésinstallation terminée. Les dossiers _OCR produits n'"'"'ont pas été touchés.\n'
}

if desinstaller; then CODE=0; else
    printf '\nÉchec de la désinstallation à l'"'"'étape %s.\n' "$ETAPE"
    CODE=1
fi
attendre_fin
exit $CODE
