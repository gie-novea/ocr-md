r"""Essai PV-02 (Windows) : création d'un raccourci .lnk sans droits d'administrateur.

Crée sortie/OCR - Essai PV-02.lnk par l'objet COM WScript.Shell appelé depuis
Windows PowerShell (aucune dépendance Python supplémentaire), puis relit ses propriétés.
Le raccourci n'est PAS placé dans SendTo : la copie dans
%APPDATA%\Microsoft\Windows\SendTo est faite à la main pour le test manuel.
Usage : ../.venv/Scripts/python creer_raccourci.py
"""
import json
import pathlib
import subprocess
import sys

ICI = pathlib.Path(__file__).parent.resolve()
lnk = ICI / "sortie" / "OCR - Essai PV-02.lnk"
cible = pathlib.Path(sys.executable).with_name("pythonw.exe")
arguments = f'"{ICI / "journal_arguments.py"}" --sortie md'


def ps(script):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, encoding="utf-8")


def echapper(s):
    return str(s).replace("'", "''")


r = ps(
    "$s = New-Object -ComObject WScript.Shell; "
    f"$l = $s.CreateShortcut('{echapper(lnk)}'); "
    f"$l.TargetPath = '{echapper(cible)}'; "
    f"$l.Arguments = '{echapper(arguments)}'; "
    f"$l.WorkingDirectory = '{echapper(ICI)}'; "
    "$l.WindowStyle = 7; $l.Save()")
lecture = ps(
    "$s = New-Object -ComObject WScript.Shell; "
    f"$l = $s.CreateShortcut('{echapper(lnk)}'); "
    "[pscustomobject]@{Cible=$l.TargetPath; Arguments=$l.Arguments} | ConvertTo-Json")
print(json.dumps({"creation_code": r.returncode, "erreur": r.stderr.strip(),
                  "lnk_existe": lnk.exists(), "relu": lecture.stdout.strip()},
                 ensure_ascii=False, indent=1))
