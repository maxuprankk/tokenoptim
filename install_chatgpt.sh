#!/usr/bin/env python3
"""
TokenSight for ChatGPT Desktop — Installation en une commande.
Point d'entrée quand l'utilisateur fait :
  curl -sS https://tokensight.app/install_chatgpt | python3

Ce script télécharge le serveur MCP dans ~/.tokensight/ et configure la licence.
Ne touche PAS au config.toml Codex — le marketplace gère ça.
"""
import urllib.request
import subprocess
import sys
import pathlib
import os

INSTALL_DIR = pathlib.Path.home() / ".tokensight"
SERVER_URL = "https://raw.githubusercontent.com/maxuprankk/tokenoptim/main/server_chatgpt.py"


def main():
    print()
    print("  ⚡ TokenSight for ChatGPT — Installation")
    print("  https://tokensight.app")
    print()

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    server_path = INSTALL_DIR / "server_chatgpt.py"

    print("📥 Téléchargement du serveur MCP...")
    try:
        urllib.request.urlretrieve(SERVER_URL, server_path)
    except Exception as e:
        print(f"❌ Échec du téléchargement : {e}")
        print(f"   URL : {SERVER_URL}")
        sys.exit(1)

    server_path.chmod(0o755)
    print(f"✅ Serveur installé → {server_path}")

    print()
    print("📦 Pour activer TokenSight dans ChatGPT :")
    print()
    print("   Méthode 1 — Plugin Marketplace (recommandé, 2 clics) :")
    print("   1. ChatGPT Desktop → Settings → Plugins → Add marketplace")
    print("   2. Entre : https://github.com/maxuprankk/tokenoptim.git")
    print("   3. Installe le plugin TokenSight")
    print()
    print("   Méthode 2 — MCP direct (si tu préfères) :")
    print("   1. Ajoute ce bloc dans ChatGPT → Settings → MCP Servers :")
    print(f"      command: /usr/local/bin/python3")
    print(f"      args: [\"{server_path}\"]")
    print()
    print("🔑 Puis active ta licence :")
    print("   tokensight activate <TA_CLE>")
    print()
    print("🎉 Redémarre ChatGPT Desktop et profite de 2x plus de requêtes !")


if __name__ == "__main__":
    main()