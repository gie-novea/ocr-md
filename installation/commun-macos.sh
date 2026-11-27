# Fonctions communes aux scripts macOS d'ocr-md (EX-69, EX-72, EX-73), chargées par « . ».
# Tout s'installe dans le profil de l'utilisateur, sans droits d'administrateur (EX-02).

# Source de distribution (EX-69) : archive du dépôt GitHub, installée par uv sans Git.
# Elle peut être remplacée par le premier argument du script (chemin d'un dossier ou d'un
# paquet « wheel », ou autre adresse) ou par la variable d'environnement OCR_MD_SOURCE.
SOURCE_PAR_DEFAUT="https://github.com/gie-novea/ocr-md/archive/refs/heads/main.zip"
VERSION_PYTHON="3.12"

source_ocr_md() {
    if [ -n "${1:-}" ]; then echo "$1"
    elif [ -n "${OCR_MD_SOURCE:-}" ]; then echo "$OCR_MD_SOURCE"
    else echo "$SOURCE_PAR_DEFAUT"; fi
}

etape() {
    ETAPE="$1"
    printf '\n[%s] %s\n' "$1" "$2"
}

chemin_uv() {
    if [ -x "$HOME/.local/bin/uv" ]; then echo "$HOME/.local/bin/uv"
    elif command -v uv >/dev/null 2>&1; then command -v uv
    fi
}

installer_uv() {
    UV="$(chemin_uv)"
    if [ -n "$UV" ]; then
        echo "uv est déjà installé : $UV"
        return 0
    fi
    echo "Installation de uv dans le profil (astral.sh)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || return 1
    UV="$(chemin_uv)"
    [ -n "$UV" ] || { echo "uv n'a pas été installé (vérifier l'accès à astral.sh et à GitHub)"; return 1; }
    echo "uv installé : $UV"
}

installer_python() {
    # uv peut signaler une erreur alors que l'installation a réussi (observation du jalon 0) :
    # le résultat est vérifié par « uv python find » plutôt que par le seul code de retour.
    "$UV" python install "$VERSION_PYTHON"
    local code=$?
    local python
    python="$("$UV" python find "$VERSION_PYTHON" 2>/dev/null)" || {
        echo "Python $VERSION_PYTHON n'a pas pu être installé par uv (code $code)"; return 1; }
    if [ "$code" -ne 0 ]; then
        echo "uv a signalé une erreur, mais Python $VERSION_PYTHON est bien installé : $python"
    else
        echo "Python $VERSION_PYTHON disponible : $python"
    fi
}

chemin_ocr_md() {
    local bin
    bin="$("$UV" tool dir --bin 2>/dev/null)"
    if [ -n "$bin" ] && [ -x "$bin/ocr-md" ]; then echo "$bin/ocr-md"
    elif command -v ocr-md >/dev/null 2>&1; then command -v ocr-md
    fi
}

version_ocr_md() {
    [ -n "${1:-}" ] && [ -x "$1" ] && "$1" --version 2>/dev/null | head -n 1
}

verification() {
    "$1" verifier
    if [ $? -eq 3 ]; then
        printf '\nUn prérequis manque (voir les lignes [X] ci-dessus). L'"'"'outil est installé ; les fichiers qui n'"'"'ont pas besoin de ce prérequis restent traités.\n'
    fi
}

confirmer() {
    # $2 : « oui » ou « non » pour un lancement sans question (essais), vide pour demander.
    case "${2:-}" in oui|o) return 0 ;; non|n) return 1 ;; esac
    local reponse
    read -r -p "$1 (o/n) " reponse
    case "$reponse" in [oOyY]*) return 0 ;; *) return 1 ;; esac
}

attendre_fin() {
    if [ -z "${OCR_MD_SANS_PAUSE:-}" ]; then
        printf '\n'
        read -r -p "Appuyer sur Entrée pour fermer " _
    fi
}
