"""PV-15 : Apple Vision, niveau de reconnaissance, lecture de la confiance et correction
linguistique (essai de diagnostic en CI macOS). Conclusion : correction désactivée par
défaut depuis le 27/11/2026 (EX-26) ; l'essai reste pour suivre l'effet de ce réglage.

(a) Réglages réellement appliqués à la requête (niveau, révision, langues, correction) et
    confiances renvoyées sur la page illisible du fichier 5, au niveau « accurate » et au
    niveau « fast » : une confiance uniforme de 1,0 ressemblerait au comportement de Live Text.
(b) Correction linguistique active puis désactivée, sur la page illisible (fichier 5, page 2)
    et les pages saines des fichiers 2 et 18 : taux de mots de référence retrouvés et taux de
    mots inconnus (EX-36).
Sortie : des nombres seulement. Le test n'échoue que si Vision ne répond pas.
"""

import platform
import statistics

import pymupdf
import pytest
from PIL import Image

from ocr_md import analyse_pdf, qualite
from tests.test_moteurs_reels import taux_retrouves

PAGES = [("pdf/05_illisible.pdf", 2), ("pdf/21_moyennement_degrade.pdf", 1), ("pdf/21_moyennement_degrade.pdf", 2),
         ("pdf/21_moyennement_degrade.pdf", 3), ("pdf/02_scanne.pdf", 1), ("pdf/02_scanne.pdf", 2), ("pdf/02_scanne.pdf", 3),
         ("pdf/02_scanne.pdf", 4), ("pdf/18_ligatures.pdf", 1), ("pdf/18_ligatures.pdf", 2)]


def image_page(racine, chemin, numero):
    page = pymupdf.open(racine / chemin)[numero - 1]
    pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
    surface = page.rect.width * page.rect.height * analyse_pdf.CM2_PAR_PT2
    return Image.frombytes("L", (pix.width, pix.height), pix.samples), surface


def requete_brute(image, niveau: str, correction: bool):
    """Requête Vision construite ici (indépendante du moteur de l'outil) : réglages relus sur
    la requête après exécution, et confiances de chaque ligne (candidat et observation)."""
    import objc
    import Vision
    from ocr_md.ocr.macos import _png
    with objc.autorelease_pool():
        r = Vision.VNRecognizeTextRequest.alloc().init()
        r.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate if niveau == "accurate"
                               else Vision.VNRequestTextRecognitionLevelFast)
        r.setRecognitionLanguages_(["fr-FR", "en-US"])
        r.setUsesLanguageCorrection_(correction)
        g = Vision.VNImageRequestHandler.alloc().initWithData_options_(_png(image), None)
        g.performRequests_error_([r], None)
        reglages = {"niveau_lu": int(r.recognitionLevel()), "revision": int(r.revision()),
                    "correction_lue": bool(r.usesLanguageCorrection()),
                    "langues_lues": [str(x) for x in (r.recognitionLanguages() or [])]}
        lignes = []
        for o in r.results() or []:
            c = o.topCandidates_(1)
            if c:
                lignes.append((str(c[0].string()), float(c[0].confidence()), float(o.confidence())))
    return reglages, lignes


def resume_confiances(lignes) -> str:
    if not lignes:
        return "aucune ligne"
    cand = [c for _, c, _ in lignes]
    obs = [o for _, _, o in lignes]
    distinctes = sorted({round(c, 2) for c in cand})
    return (f"{len(lignes)} lignes ; confiance du candidat min {min(cand):.3f} moy {statistics.mean(cand):.3f} "
            f"max {max(cand):.3f}, valeurs distinctes {distinctes[:8]}{' ...' if len(distinctes) > 8 else ''} ; "
            f"confiance de l'observation moy {statistics.mean(obs):.3f}")


@pytest.mark.macos
def test_pv15_diagnostic_vision(jeu_de_test):
    import Vision
    from ocr_md.ocr import macos
    racine, m = jeu_de_test
    print(f"\nPV-15 machine : {platform.machine()} ; macOS {platform.mac_ver()[0]}")
    try:
        revisions = Vision.VNRecognizeTextRequest.supportedRevisions()
        revisions = [int(i) for i in range(revisions.firstIndex(), revisions.lastIndex() + 1)
                     if revisions.containsIndex_(i)]
    except Exception as e:  # pragma: no cover - diagnostic
        revisions = f"inconnues ({type(e).__name__})"
    print(f"PV-15 révisions prises en charge : {revisions} ; révision par défaut : "
          f"{int(Vision.VNRecognizeTextRequest.defaultRevision())} ; "
          f"niveaux : accurate={int(Vision.VNRequestTextRecognitionLevelAccurate)} "
          f"fast={int(Vision.VNRequestTextRecognitionLevelFast)}")

    # (a) Réglages effectifs et confiances sur la page illisible.
    image, _ = image_page(racine, "pdf/05_illisible.pdf", 2)
    for niveau in ("accurate", "fast"):
        for correction in (True, False):
            reglages, lignes = requete_brute(image, niveau, correction)
            print(f"PV-15 (a) page illisible, {niveau}, correction {'oui' if correction else 'non'} : {reglages} ; "
                  f"{resume_confiances(lignes)}")
    # Confiance lue par le moteur de l'outil (même chemin que la production, avec correction).
    resultat = macos.MoteurMacos(correction_linguistique=True).reconnaitre(image)
    confiances = [l.confiance for l in resultat.lignes if l.confiance is not None]
    print(f"PV-15 (a) moteur de l'outil, page illisible : {len(confiances)} lignes, confiance moyenne "
          f"{statistics.mean(confiances) if confiances else float('nan'):.3f}")

    # (b) Correction linguistique active ou non : mots retrouvés et mots inconnus.
    lexique = qualite.Lexique()
    moteurs = {"avec correction": macos.MoteurMacos(correction_linguistique=True),
               "sans correction (défaut)": macos.MoteurMacos()}
    for chemin, numero in PAGES:
        f = next(x for x in m["fichiers"] if x["chemin"] == chemin)
        image, surface = image_page(racine, chemin, numero)
        mesures = []
        for nom, moteur in moteurs.items():
            r = moteur.reconnaitre(image)
            texte = "\n".join(" ".join(mot.texte for mot in l.mots) for l in r.lignes)
            ind = qualite.calculer(texte, lexique, surface)
            confiances = [l.confiance for l in r.lignes if l.confiance is not None]
            mesures.append(f"{nom} : retrouvés {taux_retrouves([f['texte_reference'][numero - 1]], texte):.1%}, "
                           f"inconnus {ind.taux_mots_inconnus:.3f} ({ind.mots_evaluables} évaluables), "
                           f"fragmentés {ind.taux_mots_fragmentes:.3f}, confiance moyenne "
                           f"{statistics.mean(confiances) if confiances else float('nan'):.3f}")
        etat = "dégradée" if numero in f.get("pages_douteuses", []) else "saine"
        print(f"PV-15 (b) {chemin} p. {numero} ({etat}) : " + " ; ".join(mesures))
