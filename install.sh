#!/usr/bin/env python3
"""
TokenSight for Claude Desktop — Installation en une commande.
Point d'entrée quand l'utilisateur fait :
  curl -sS https://tokensight.app/install | python3

Ce script télécharge et exécute l'installateur Claude.
"""

import urllib.request
import tempfile
import subprocess
import sys

INSTALLER_URL = "https://raw.githubusercontent.com/maxuprankk/tokenoptim/main/install.py"
SERVER_URL = "https://raw.githubusercontent.com/maxuprankk/tokenoptim/main/server.py"


def main():
    print("⚡ TokenSight for Claude Desktop — Installation...")
    print()

    tmpdir = tempfile.mkdtemp(prefix="tokensight-")
    installer_path = f"{tmpdir}/install.py"
    server_path = f"{tmpdir}/server.py"

    print("📥 Téléchargement de l'installateur...")
    urllib.request.urlretrieve(INSTALLER_URL, installer_path)
    urllib.request.urlretrieve(SERVER_URL, server_path)

    print("🔧 Lancement de l'installation...")
    result = subprocess.run([sys.executable, installer_path], cwd=tmpdir)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()