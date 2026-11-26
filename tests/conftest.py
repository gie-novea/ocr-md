"""Configuration commune des tests.

- Le réseau est neutralisé pour TOUS les tests (EX-03) : toute connexion sortante lève
  une erreur. Un test qui aurait besoin du réseau échouerait, ce qui est voulu.
- Les tests marqués « windows » ou « macos » ne s'exécutent que sur leur plateforme.
- Le dossier de configuration de l'utilisateur est redirigé vers un dossier temporaire,
  pour qu'un fichier réel du poste n'influe jamais sur les tests.
"""

import socket
import sys

import pytest


class ConnexionInterdite(RuntimeError):
    pass


def _refuser(*args, **kwargs):
    raise ConnexionInterdite("connexion réseau interdite pendant les tests (EX-03)")


@pytest.fixture(autouse=True)
def reseau_neutralise(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _refuser)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuser)
    monkeypatch.setattr(socket, "create_connection", _refuser)
    monkeypatch.setattr(socket, "getaddrinfo", _refuser)


@pytest.fixture(autouse=True)
def profil_isole(monkeypatch, tmp_path):
    from ocr_md import plateforme
    monkeypatch.setattr(plateforme, "fichier_configuration", lambda: tmp_path / "profil" / "config.toml")


def pytest_collection_modifyitems(config, items):
    plateformes = {"windows": "win32", "macos": "darwin"}
    for item in items:
        for marqueur, valeur in plateformes.items():
            if item.get_closest_marker(marqueur) and sys.platform != valeur:
                item.add_marker(pytest.mark.skip(reason=f"test propre à {marqueur}"))
