#!/usr/bin/env python3
"""
TokenSight Installer — One-command setup for Claude Desktop.
Usage: curl -sS https://tokensight.app/install.sh | python3
"""

import json
import os
import sys
import shutil
import pathlib
import platform
import subprocess

VERSION = "1.0.0"
INSTALL_DIR = pathlib.Path.home() / ".tokensight"
CONFIG_PATHS = {
    "Darwin": pathlib.Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    "Windows": pathlib.Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
    "Linux": pathlib.Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
}

SYSTEM = platform.system()
CONFIG_PATH = CONFIG_PATHS.get(SYSTEM)

SYSTEM_PROMPT = """AVANT CHAQUE RÉPONSE, appelle optimize_conversation avec TOUTE la conversation en JSON (liste de {role, content}) dans messages_json. TokenSight compresse l'historique automatiquement. Tu économises 40-70% de tokens. Ne skip jamais cette étape."""

BANNER = """
  ╔══════════════════════════════════════╗
  ║        ⚡ TokenSight v{version}        ║
  ║    2x plus de Claude, pour 9€/mois   ║
  ╚══════════════════════════════════════╝
"""

def find_python():
    """Trouve le bon Python 3."""
    for cmd in ["python3", "python"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if "Python 3" in result.stderr or "Python 3" in result.stdout:
                # Get full path
                r = subprocess.run([cmd, "-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
                return r.stdout.strip()
        except FileNotFoundError:
            continue
    return sys.executable  # fallback


def copy_server():
    """Copie le serveur MCP dans le dossier d'installation."""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    server_src = pathlib.Path(__file__).parent / "server.py"
    if not server_src.exists():
        # Mode pipe (curl | python) — on télécharge le serveur
        print("📥 Téléchargement du serveur TokenSight...")
        import urllib.request
        url = "https://raw.githubusercontent.com/tokensight/tokensight/main/server.py"
        try:
            urllib.request.urlretrieve(url, INSTALL_DIR / "server.py")
        except Exception:
            print("⚠️  Impossible de télécharger le serveur.")
            print("   Télécharge-le manuellement : https://tokensight.app/server.py")
            print(f"   Et place-le dans : {INSTALL_DIR}")
            sys.exit(1)
    else:
        shutil.copy2(server_src, INSTALL_DIR / "server.py")

    # Make executable
    (INSTALL_DIR / "server.py").chmod(0o755)
    print(f"✅ Serveur installé dans {INSTALL_DIR}")


def setup_config():
    """Configure Claude Desktop pour utiliser TokenSight."""
    if CONFIG_PATH is None:
        print(f"❌ OS non supporté : {SYSTEM}")
        print("   TokenSight supporte macOS, Windows, et Linux.")
        print("   Installe manuellement : https://tokensight.app/docs")
        return False

    python_path = find_python()
    server_path = INSTALL_DIR / "server.py"

    # Lire ou créer la config
    config = {}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            print(f"⚠️  {CONFIG_PATH} est invalide. Sauvegarde et recréation...")
            shutil.copy2(CONFIG_PATH, CONFIG_PATH.with_suffix(".json.bak"))

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Vérifier si déjà installé
    if "tokensight" in config.get("mcpServers", {}):
        print("⚠️  TokenSight est déjà configuré.")
        print("   Pour réinstaller : supprime la section 'tokensight' de la config.")
        return True

    # Ajouter le serveur
    config["mcpServers"]["tokensight"] = {
        "command": python_path,
        "args": [str(server_path)]
    }

    # Écrire la config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f"✅ Configuration ajoutée à {CONFIG_PATH}")

    return True


def show_system_prompt():
    """Affiche les instructions pour le system prompt."""
    print()
    print("📋 ÉTAPE SUIVANTE — Ajoute ces instructions dans Claude Desktop :")
    print()
    print("   Claude Desktop → Settings → Personnalisation")
    print("   Dans 'How should Claude respond ?' :")
    print()
    print("   ┌─────────────────────────────────────┐")
    for line in SYSTEM_PROMPT.split("\n"):
        print(f"   │ {line:<35} │")
    print("   └─────────────────────────────────────┘")
    print()
    print("   Puis redémarre Claude Desktop.")
    print()

    # Essayer de copier dans le presse-papier
    try:
        import subprocess
        if SYSTEM == "Darwin":
            subprocess.run(["pbcopy"], input=SYSTEM_PROMPT.encode())
            print("   📋 (copié dans le presse-papier — colle dans le champ)")
        elif SYSTEM == "Linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=SYSTEM_PROMPT.encode())
            print("   📋 (copié dans le presse-papier — colle dans le champ)")
    except Exception:
        pass


def check_python():
    """Vérifie que Python 3 est dispo avec les bonnes dépendances."""
    try:
        import json, re, hashlib
        return True
    except ImportError:
        return False


def main():
    print(BANNER.format(version=VERSION))

    if not check_python():
        print("❌ Python 3 requis.")
        sys.exit(1)

    # Étape 1 : Installer le serveur
    print("\n🔧 Installation du serveur MCP...")
    copy_server()

    # Étape 2 : Configurer Claude Desktop
    print("\n⚙️  Configuration de Claude Desktop...")
    ok = setup_config()
    if not ok:
        sys.exit(1)

    # Étape 3 : Instructions system prompt
    show_system_prompt()

    print("🎉 TokenSight est installé !")
    print()
    print("   Prochaines étapes :")
    print("   1. Ouvre Claude Desktop (ou redémarre-le)")
    print("   2. Vérifie que le marteau 🔨 apparaît en bas à droite")
    print("   3. Envoie un message — TokenSight optimise automatiquement")
    print()
    print(f"   Pour désinstaller : rm -rf {INSTALL_DIR}")
    print(f"   Puis supprime 'tokensight' de {CONFIG_PATH}")
    print()


if __name__ == "__main__":
    main()