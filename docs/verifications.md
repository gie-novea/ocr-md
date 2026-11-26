# Vérifications des points PV-xx

Ce fichier consigne, pour chaque point à vérifier du cahier des charges (section 10), le résultat de l'essai, la date, les versions, la décision et le repli éventuel. Les scripts d'essai sont dans `essais/`.

Poste de développement : Windows 11 Pro (10.0.26300), compte de l'utilisateur, uv 0.11.21, Python 3.12.

| Point | État | Résumé |
|---|---|---|
| PV-01 | à lever par le référent | poste SODEB sous compte standard |
| PV-02 | en cours | partie Windows |
| PV-03 | levé pour le poste de développement | voir ci-dessous |
| PV-04 | en cours | |
| PV-05 | en cours | |
| PV-06 | en cours | |
| PV-07 | hors v1 | v1.1 |
| PV-08 | à lever par la CI macOS et le référent | |
| PV-09 | en cours | script de diagnostic |
| PV-10 | à lever par le référent | |
| PV-11 | en cours | |
| PV-12 | en cours | |
| PV-13 | en cours | |

## PV-03. Pack OCR français de Windows

- Date : 26/11/2026.
- Méthode : Windows PowerShell 5.1, compte non élevé : `[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages`.
- Résultat : `en-US` et `fr-FR` disponibles ; appel sans élévation réussi ; `MaxImageDimension` = 10000.
- Décision : la méthode de détection sans droits d'administrateur (EX-71) est confirmée. La présence du pack sur les PC de la SODEB reste à constater par `ocr-md verifier`.
