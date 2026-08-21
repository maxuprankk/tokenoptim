#!/usr/bin/env python3
"""
TokenSight CLI — activate, status, uninstall.
Usage: tokensight activate <key>
       tokensight status
       tokensight uninstall
"""

import json, pathlib, hashlib, uuid, os, time, sys, re

HOME = pathlib.Path.home()
TOKENSIGHT_DIR = HOME / ".tokensight"
LICENSE_FILE = TOKENSIGHT_DIR / "license.json"

# ─── BACKEND EN POINT FINAL (à remplacer par ton serveur) ───
API_URL = "https://api.tokensight.app/v1"


def machine_id():
    return hashlib.sha256(
        (str(uuid.getnode()) + os.environ.get("USER", "")).encode()
    ).hexdigest()[:12]


def activate(key: str):
    """Valide et sauvegarde une licence."""
    if not re.match(r'^ts_[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$', key):
        print("❌ Format de clé invalide.")
        print("   Format attendu : ts_xxxx-xxxx-xxxx-xxxx")
        print("   Va sur https://tokensight.app pour obtenir ta clé.")
        sys.exit(1)

    print("🔑 Validation de la clé...")

    # En prod : appel API pour valider la clé + récupérer les infos
    # Pour le proto : on accepte le format et on simule
    license_data = {
        "key_hash": hashlib.sha256(key.encode()).hexdigest()[:16],
        "email": "user@example.com",
        "plan": "pro",
        "activated_at": int(time.time()),
        "exp": int(time.time()) + 30 * 24 * 3600,
        "machine_id": machine_id(),
        "trial": True
    }

    TOKENSIGHT_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(json.dumps(license_data, indent=2))

    print("✅ TokenSight activé !")
    print(f"   Plan : {license_data['plan'].upper()}")
    print(f"   Essai gratuit : 30 jours")
    print(f"   Expire le : {time.strftime('%d/%m/%Y', time.localtime(license_data['exp']))}")
    print()
    print("   Redémarre ChatGPT pour que la licence soit prise en compte.")


def status():
    """Affiche l'état de la licence."""
    if not LICENSE_FILE.exists():
        print("❌ Aucune licence trouvée.")
        print("   Lance `tokensight activate <TA_CLE>` ou va sur https://tokensight.app")
        sys.exit(1)

    try:
        lic = json.loads(LICENSE_FILE.read_text())
    except json.JSONDecodeError:
        print("❌ Fichier de licence corrompu.")
        sys.exit(1)

    exp = lic.get("exp", 0)
    remaining = max(0, exp - time.time())
    days = int(remaining / 86400)
    expired = time.time() > exp

    print("📊 TokenSight Status")
    print(f"   Plan      : {lic.get('plan', 'unknown').upper()}")
    print(f"   Email     : {lic.get('email', 'inconnu')}")
    print(f"   Expire    : {time.strftime('%d/%m/%Y', time.localtime(exp)) if exp else '∞'}")
    print(f"   Restant   : {days} jours" if not expired else "   ❌ EXPIRÉE")
    print(f"   Trial     : {'Oui' if lic.get('trial') else 'Non'}")

    if expired:
        print()
        print("   🔄 Renouvelle sur https://tokensight.app")
        sys.exit(1)


def uninstall():
    """Désinstalle proprement."""
    print("🗑️  Désinstallation de TokenSight...")

    if TOKENSIGHT_DIR.exists():
        import shutil
        shutil.rmtree(TOKENSIGHT_DIR)
        print(f"   ✅ {TOKENSIGHT_DIR} supprimé")

    # Nettoyer Codex config
    codex_config = HOME / ".codex" / "config.toml"
    if codex_config.exists():
        text = codex_config.read_text()
        if "[mcp_servers.tokensight]" in text:
            # Retirer la section tokensight
            lines = text.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if line.strip() == "[mcp_servers.tokensight]":
                    skip = True
                    continue
                if skip and line.strip().startswith("[") and line.strip() != "[mcp_servers.tokensight]":
                    skip = False
                if skip and line.strip():
                    continue
                if skip and not line.strip():
                    skip = False
                    continue
                if not skip:
                    new_lines.append(line)
            codex_config.write_text("\n".join(new_lines))
            print(f"   ✅ Section tokensight retirée de {codex_config}")

    # Nettoyer Claude config
    claude_config = HOME / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if claude_config.exists():
        try:
            cfg = json.loads(claude_config.read_text())
            if "tokensight" in cfg.get("mcpServers", {}):
                del cfg["mcpServers"]["tokensight"]
                claude_config.write_text(json.dumps(cfg, indent=2))
                print(f"   ✅ Section tokensight retirée de {claude_config}")
        except (json.JSONDecodeError, KeyError):
            pass

    print()
    print("🎉 TokenSight désinstallé.")


def main():
    if len(sys.argv) < 2:
        print("TokenSight CLI v1.0")
        print()
        print("  tokensight activate <clé>    Activer une licence")
        print("  tokensight status             Voir l'état")
        print("  tokensight uninstall          Désinstaller")
        print()
        print("  https://tokensight.app")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "activate":
        if len(sys.argv) < 3:
            print("❌ Usage: tokensight activate <clé>")
            sys.exit(1)
        activate(sys.argv[2])
    elif cmd == "status":
        status()
    elif cmd == "uninstall":
        uninstall()
    else:
        print(f"❌ Commande inconnue : {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()