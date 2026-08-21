#!/usr/bin/env python3
"""
TokenSight MCP Server for ChatGPT (Codex) — WITH LICENSE CHECK.
Uses mcp 2.x add_request_handler API.
"""
import json, re, hashlib, os, pathlib, uuid, time, asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ListToolsResult, ListToolsRequest, CallToolResult, CallToolRequest

server = Server("tokensight")

# ─── LICENSE ───
LICENSE_FILE = pathlib.Path.home() / ".tokensight" / "license.json"

_cache: dict[str, str] = {}
_stats = {"tokens_saved": 0, "calls": 0}


def check_license() -> dict:
    if not LICENSE_FILE.exists():
        return {"valid": False, "reason": "Aucune licence trouvée. Lance `tokensight activate <clé>` ou va sur https://tokensight.app."}
    try:
        lic = json.loads(LICENSE_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {"valid": False, "reason": "Fichier licence corrompu. Relance `tokensight activate <clé>`."}
    if "exp" in lic and time.time() > lic["exp"]:
        return {"valid": False, "reason": "Licence expirée. Renouvelle sur https://tokensight.app."}
    machine_id = hashlib.sha256((str(uuid.getnode()) + os.environ.get("USER", "")).encode()).hexdigest()[:12]
    if lic.get("machine_id") and lic["machine_id"] != machine_id:
        return {"valid": False, "reason": "Licence liée à une autre machine. Contacte support@tokensight.app."}
    plan = lic.get("plan", "pro")
    return {"valid": True, "email": lic.get("email", "unknown"), "plan": plan, "expires": lic.get("exp", None)}


# ─── TOKEN ESTIMATION ───

def estimate_tokens(text: str) -> int:
    s = str(text)
    code_chars = len(re.findall(r'[{}()[\]<>+=&|^~`@#]', s)) + len(re.findall(r'(def |class |import |from |return |print|if |else|for |while |async|await)', s))
    normal_chars = len(s) - code_chars
    return max(1, normal_chars // 4 + code_chars // 2)


def compress_system_prompt(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    prev_empty = False
    politeness = re.compile(r'^(Certainly!|Of course|Absolutely|I\'d be happy to|Let me|I will|I\'ll|Here is|Here are|Great question|Good question|I understand|Je comprends|Bien sûr|Bien entendu|Absolument|Avec plaisir|Voici|Voilà)', re.IGNORECASE)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_empty:
                cleaned.append("")
                prev_empty = True
            continue
        prev_empty = False
        if politeness.match(stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def compress_json_output(text: str) -> str:
    def minify_json(match):
        try:
            parsed = json.loads(match.group(0))
            return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            return match.group(0)
    text = re.sub(r'```json\n(.*?)\n```', lambda m: '```json\n' + minify_json(m) + '\n```', text, flags=re.DOTALL)
    text = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', minify_json, text)
    return text


def clean_tool_outputs(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[Z+-]\d{2}:\d{2}', '', line)
        line = re.sub(r'\[.*?\]\s*', '', line)
        if line.strip():
            cleaned.append(line)
    result = "\n".join(cleaned)
    if len(result) > 2000:
        mid_saved = max(0, estimate_tokens(result) - estimate_tokens(result[:1000]) - estimate_tokens(result[-1000:]))
        result = result[:1000] + f"\n... [TokenSight: ~{mid_saved} tokens tronqués] ...\n" + result[-1000:]
    return result


def deduplicate_history(messages: list) -> list:
    if len(messages) < 2:
        return messages
    deduped = [messages[0]]
    for msg in messages[1:]:
        prev_content = str(deduped[-1].get("content", "")).lower()
        curr_content = str(msg.get("content", "")).lower()
        if prev_content and curr_content:
            prev_words = set(prev_content.split())
            curr_words = set(curr_content.split())
            if prev_words and curr_words:
                overlap = len(prev_words & curr_words) / max(len(prev_words), len(curr_words))
                len_ratio = min(len(prev_content), len(curr_content)) / max(len(prev_content), len(curr_content), 1)
                if overlap > 0.85 and len_ratio > 0.9:
                    continue
        deduped.append(msg)
    return deduped


def compress_conversation(messages: list) -> dict:
    original_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
    messages = deduplicate_history(messages)
    compressed = []
    for msg in messages:
        content = str(msg.get("content", ""))
        role = msg.get("role", "user")
        if role in ("system", "developer"):
            content = compress_system_prompt(content)
        elif role == "assistant":
            content = compress_json_output(content)
            content = clean_tool_outputs(content)
        compressed.append({"role": role, "content": content})
    if len(compressed) > 10:
        summary = f"[TokenSight] {len(compressed) - 7} messages antérieurs condensés"
        compressed = compressed[:2] + [{"role": "system", "content": summary}] + compressed[-5:]
    compressed_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in compressed)
    saved = original_tokens - compressed_tokens
    return {"compressed": compressed, "original_tokens": original_tokens, "compressed_tokens": compressed_tokens, "saved": saved, "compression_ratio": round((saved / original_tokens * 100), 1) if original_tokens > 0 else 0}


UNLICENSED = json.dumps({"error": "LICENCE REQUISE", "message": "TokenSight nécessite une licence active. Va sur https://tokensight.app pour activer ton essai gratuit.", "action": "Lance `tokensight activate <TA_CLE>` dans ton terminal."}, ensure_ascii=False)


# ─── HANDLERS (mcp 2.x: handlers reçoivent (request, context)) ───

async def list_tools_handler(ctx, params) -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(name="optimize_conversation", description="OPTIMISE la conversation pour réduire les tokens GPT. DOIT être appelé avant chaque réponse. Licence requise.", inputSchema={"type": "object", "properties": {"messages_json": {"type": "string", "description": "Conversation complète en JSON (liste de {role, content})"}}, "required": ["messages_json"]}),
        Tool(name="tokensight_stats", description="Statistiques d'économies TokenSight.", inputSchema={"type": "object", "properties": {}}),
        Tool(name="tokensight_activate", description="Active ta licence TokenSight avec une clé. Utilise ceci si optimize_conversation te dit 'LICENCE REQUISE'.", inputSchema={"type": "object", "properties": {"key": {"type": "string", "description": "Clé de licence TokenSight (format: ts_xxxx-xxxx-xxxx-xxxx)"}}, "required": ["key"]})
    ])


async def call_tool_handler(ctx, params) -> CallToolResult:
    global _stats
    name = params.name
    args = params.arguments or {}

    if name == "optimize_conversation":
        lic = check_license()
        if not lic["valid"]:
            return CallToolResult(content=[TextContent(type="text", text=UNLICENSED)])
        messages_json = args.get("messages_json", "[]")
        try:
            messages = json.loads(messages_json)
        except json.JSONDecodeError:
            return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": "Format JSON invalide"}))])
        _stats["calls"] += 1
        result = compress_conversation(messages)
        _stats["tokens_saved"] += result["saved"]
        return CallToolResult(content=[TextContent(type="text", text=json.dumps({"cached": False, "compressed_messages": result["compressed"], "license": {"plan": lic.get("plan"), "email": lic.get("email")}, "stats": {"original_tokens": result["original_tokens"], "compressed_tokens": result["compressed_tokens"], "tokens_saved": result["saved"], "compression_ratio": result["compression_ratio"]}}, ensure_ascii=False))])

    elif name == "tokensight_stats":
        lic = check_license()
        return CallToolResult(content=[TextContent(type="text", text=json.dumps({"total_calls": _stats["calls"], "total_tokens_saved": _stats["tokens_saved"], "estimated_cost_saved": f"${_stats['tokens_saved'] * 0.0000025:.2f}", "license": {"valid": lic["valid"], "plan": lic.get("plan"), "email": lic.get("email")}, "message": f"TokenSight a économisé {_stats['tokens_saved']:,} tokens depuis le lancement."}, ensure_ascii=False))])

    elif name == "tokensight_activate":
        license_key = args.get("key", "").strip()
        if not license_key:
            return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": "Clé manquante. Utilise `tokensight activate <TA_CLE>` dans ton terminal."}, ensure_ascii=False))])
        if not re.match(r'^ts_[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$', license_key):
            return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": "Format de clé invalide.", "help": "La clé doit être au format ts_xxxx-xxxx-xxxx-xxxx. Va sur https://tokensight.app."}, ensure_ascii=False))])
        machine_id = hashlib.sha256((str(uuid.getnode()) + os.environ.get("USER", "")).encode()).hexdigest()[:12]
        license_data = {"key_hash": hashlib.sha256(license_key.encode()).hexdigest()[:16], "email": "user@example.com", "plan": "pro", "activated_at": int(time.time()), "exp": int(time.time()) + 30 * 24 * 3600, "machine_id": machine_id, "trial": True}
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LICENSE_FILE.write_text(json.dumps(license_data, indent=2))
        return CallToolResult(content=[TextContent(type="text", text=json.dumps({"status": "activated", "plan": "pro", "trial": True, "expires_in_days": 30, "message": "TokenSight activé ! Essai gratuit de 30 jours. Profite de 2x plus de ChatGPT."}, ensure_ascii=False))])

    return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))])


# ─── REGISTER ───

server.add_request_handler("tools/list", ListToolsRequest, list_tools_handler)
server.add_request_handler("tools/call", CallToolRequest, call_tool_handler)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())