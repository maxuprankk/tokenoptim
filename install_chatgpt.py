#!/usr/bin/env python3
"""
TokenSight Installer for ChatGPT Desktop.
Usage local : python3 install_chatgpt.py
Via curl    : curl -sS https://tokensight.app/install_chatgpt | python3

Ce script :
  1. Télécharge/copie le serveur MCP dans ~/.tokensight/
  2. Vérifie que la licence est active (ou guide l'utilisateur)
  3. Affiche les instructions pour activer le MCP (plugin marketplace ou direct)

Ne modifie PAS le config.toml Codex — le plugin marketplace gère ça.
"""

import os
import sys
import shutil
import pathlib
import subprocess
import urllib.request

VERSION = "1.0.0"
INSTALL_DIR = pathlib.Path.home() / ".tokensight"
SERVER_URL = "https://raw.githubusercontent.com/maxuprankk/tokenoptim/main/server_chatgpt.py"

BANNER = """
  ╔══════════════════════════════════════╗
  ║     ⚡ TokenSight for ChatGPT v{version}  ║
  ║    2x plus de ChatGPT, pour 9€/mois  ║
  ╚══════════════════════════════════════╝
"""


def download_server():
    """Télécharge le serveur MCP depuis GitHub."""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    server_path = INSTALL_DIR / "server_chatgpt.py"

    # Si on est en local (fichier à côté), on copie
    local_src = pathlib.Path(__file__).parent / "server_chatgpt.py"
    if local_src.exists():
        shutil.copy2(local_src, server_path)
        print(f"✅ Serveur copié depuis le projet local")
    else:
        # Mode téléchargement (via curl)
        print("📥 Téléchargement du serveur TokenSight...")
        try:
            urllib.request.urlretrieve(SERVER_URL, server_path)
        except Exception as e:
            print(f"⚠️  Téléchargement impossible : {e}")
            print(f"   Télécharge manuellement : {SERVER_URL}")
            print(f"   Place le fichier dans : {server_path}")
            sys.exit(1)

    server_path.chmod(0o755)
    print(f"✅ Serveur installé → {server_path}")


def check_license():
    """Vérifie si une licence est active."""
    license_file = INSTALL_DIR / "license.json"
    if not license_file.exists():
        return False

    try:
        import json, time
        lic = json.loads(license_file.read_text())
        if "exp" in lic and time.time() > lic["exp"]:
            return False
        return True
    except Exception:
        return False


def find_python():
    """Trouve le python3 system."""
    for cmd in ["python3", "python"]:
        try:
            r = subprocess.run([cmd, "-c", "import sys; print(sys.executable)"],
                             capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout.strip()
        except FileNotFoundError:
            continue
    return sys.executable


def main():
    print(BANNER.format(version=VERSION))

    print("🔧 Installation du serveur MCP...")
    download_server()

    print()
    has_license = check_license()
    if not has_license:
        print("🔑 Aucune licence trouvée. Active ta licence :")
        print()
        print("   tokensight activate <TA_CLE>")
        print()
        print("   Pas de clé ? Va sur https://tokensight.app")
        print("   (Pour le prototype, utilise : tokensight activate ts_demo-1234-abcd-5678)")
    else:
        print("✅ Licence active — TokenSight est prêt !")

    python_path = find_python()
    server_path = INSTALL_DIR / "server_chatgpt.py"

    print()
    print("📦 Pour connecter TokenSight à ChatGPT — 2 méthodes :")
    print()
    print("   ┌─ Méthode 1 : Plugin Marketplace (recommandé, 2 clics) ───────────┐")
    print("   │ 1. ChatGPT Desktop → Settings → Plugins → Add marketplace         │")
    print("   │ 2. URL : https://github.com/maxuprankk/tokenoptim.git             │")
    print("   │ 3. Installe le plugin TokenSight                                  │")
    print("   │ → Le serveur MCP est spawné automatiquement.                      │")
    print("   └───────────────────────────────────────────────────────────────────┘")
    print()
    print("   ┌─ Méthode 2 : MCP direct (si tu préfères) ────────────────────────┐")
    print("   │ ChatGPT → Settings → MCP Servers → Add :                          │")
    print(f"   │   command: {python_path}                                           │")
    print(f"   │   args: [\"{server_path}\"]")
    print("   │ → Puis redémarre ChatGPT.                                         │")
    print("   └───────────────────────────────────────────────────────────────────┘")

    print()
    print("🎉 TokenSight est installé !")
    print(f"   Pour désinstaller : rm -rf {INSTALL_DIR}")
    print(f"   + supprime le marketplace dans ChatGPT → Settings → Plugins")


if __name__ == "__main__":
    main()