"""Construit le lexique embarqué à partir du lexique de Grammalecte (MPL 2.0).

Entrée : l'archive officielle lexique-grammalecte-fr-v7.7.zip, téléchargée depuis
https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip ; son empreinte SHA-256 est
contrôlée. Sortie : src/ocr_md/donnees/lexique/formes-fr.txt.gz, une forme fléchie par
ligne (NFC, sans doublon, triée), précédée de l'avis de licence MPL 2.0 d'origine, qui
doit être conservé (le fichier dérivé reste sous MPL 2.0).
Usage : python outils/construire_lexique.py CHEMIN_DE_L_ARCHIVE
"""

import gzip
import hashlib
import io
import pathlib
import sys
import unicodedata
import zipfile

URL = "https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip"
SHA256 = "bdccf2065e252010253171000a38de84581407896b6bc60aca7d4d69dab7e4d2"
MEMBRE = "lexique-grammalecte-fr-v7.7.txt"
SORTIE = pathlib.Path(__file__).parents[1] / "src" / "ocr_md" / "donnees" / "lexique" / "formes-fr.txt.gz"

ENTETE = f"""# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Lexique des formes fléchies du français - Grammalecte v7.7 (Olivier R., Dicollecte)
# Licence : MPL v2.0
# Fichier dérivé pour ocr-md : colonne « Flexion » seule, normalisée NFC, sans doublon.
# Source : {URL}
# SHA-256 de l'archive source : {SHA256}
"""


def main():
    archive = pathlib.Path(sys.argv[1])
    empreinte = hashlib.sha256(archive.read_bytes()).hexdigest()
    if empreinte != SHA256:
        sys.exit(f"empreinte inattendue : {empreinte}")
    formes = set()
    with zipfile.ZipFile(archive) as z, z.open(MEMBRE) as f:
        en_tete_vu = False
        for ligne in io.TextIOWrapper(f, encoding="utf-8"):
            if not en_tete_vu:
                en_tete_vu = ligne.startswith("id\tfid\tFlexion")
                continue
            champs = ligne.rstrip("\n").split("\t")
            if len(champs) > 2 and champs[2]:
                formes.add(unicodedata.normalize("NFC", champs[2]))
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    contenu = ENTETE + "\n".join(sorted(formes)) + "\n"
    # mtime=0 : archive reproductible octet pour octet.
    with open(SORTIE, "wb") as brut, gzip.GzipFile(fileobj=brut, mode="wb", mtime=0, filename="") as gz:
        gz.write(contenu.encode("utf-8"))
    print(f"{len(formes)} formes ; {SORTIE.stat().st_size} octets ; {SORTIE}")


if __name__ == "__main__":
    main()
