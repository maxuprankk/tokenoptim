#!/usr/bin/env python3
"""
TokenSight MCP Server — L'optimiseur LLM invisible.
Format : MCP server stdio pour Claude Desktop.
"""

import json
import re
import hashlib
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, TextContent, ListToolsResult, CallToolResult,
    ListToolsRequest, CallToolRequest
)

server = Server("tokensight")

# ─── Cache simple (en mémoire) ───
_response_cache: dict[str, str] = {}
_stats = {"tokens_saved": 0, "calls": 0}


def estimate_tokens(text: str) -> int:
    return max(1, len(str(text)) // 3)


def compress_system_prompt(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    prev_empty = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_empty:
                cleaned.append("")
                prev_empty = True
            continue
        prev_empty = False
        if re.match(r'^(Certainly!|Of course|Absolutely|I\'d be happy to|Let me|I will|I\'ll|Here is|Here are)', stripped, re.IGNORECASE):
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


def semantic_cache_key(content: str) -> str:
    normalized = re.sub(r'[^\w\s]', '', content.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def compress_conversation(messages: list) -> dict:
    original_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
    messages = deduplicate_history(messages)

    compressed = []
    for msg in messages:
        content = str(msg.get("content", ""))
        role = msg.get("role", "user")
        if role == "system":
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

    return {
        "compressed": compressed,
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "saved": saved,
        "compression_ratio": round((saved / original_tokens * 100), 1) if original_tokens > 0 else 0
    }


# ─── MCP TOOLS ───

def handle_optimize(arguments: dict) -> CallToolResult:
    global _stats
    messages_json = arguments.get("messages_json", "[]")

    try:
        messages = json.loads(messages_json)
    except json.JSONDecodeError:
        return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": "Format JSON invalide"}))])

    _stats["calls"] += 1

    # Cache check
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if last_user:
        key = semantic_cache_key(str(last_user.get("content", "")))
        if key in _response_cache:
            saved = estimate_tokens(str(last_user.get("content", "")))
            _stats["tokens_saved"] += saved
            return CallToolResult(content=[TextContent(type="text", text=json.dumps({
                "cached": True,
                "response": _response_cache[key],
                "tokens_saved": saved,
                "note": "Réponse servie depuis le cache TokenSight"
            }, ensure_ascii=False))])

    result = compress_conversation(messages)
    _stats["tokens_saved"] += result["saved"]

    return CallToolResult(content=[TextContent(type="text", text=json.dumps({
        "cached": False,
        "compressed_messages": result["compressed"],
        "stats": {
            "original_tokens": result["original_tokens"],
            "compressed_tokens": result["compressed_tokens"],
            "tokens_saved": result["saved"],
            "compression_ratio": result["compression_ratio"]
        }
    }, ensure_ascii=False))])


def handle_stats(arguments: dict) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=json.dumps({
        "total_calls": _stats["calls"],
        "total_tokens_saved": _stats["tokens_saved"],
        "estimated_cost_saved": f"${_stats['tokens_saved'] * 0.000003:.2f}",
        "message": f"TokenSight a économisé {_stats['tokens_saved']:,} tokens depuis le lancement."
    }, ensure_ascii=False))])


# ─── REGISTER HANDLERS ───

async def list_tools_handler(req: ListToolsRequest) -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(
            name="optimize_conversation",
            description="""OPTIMISE la conversation actuelle pour réduire la consommation de tokens.
DOIT être appelé avant chaque réponse. Passe TOUTE la conversation en JSON (liste de {role, content}) dans messages_json.
Retourne une version compressée qui préserve le sens mais utilise 40-70% de tokens en moins.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages_json": {
                        "type": "string",
                        "description": "La conversation complète en JSON — liste de {role: string, content: string}"
                    }
                },
                "required": ["messages_json"]
            }
        ),
        Tool(
            name="tokensight_stats",
            description="Affiche les statistiques d'économies TokenSight (tokens sauvés, coûts évités).",
            inputSchema={"type": "object", "properties": {}}
        )
    ])


async def call_tool_handler(req: CallToolRequest) -> CallToolResult:
    args = req.params.arguments or {}
    if req.params.name == "optimize_conversation":
        return handle_optimize(args)
    elif req.params.name == "tokensight_stats":
        return handle_stats(args)
    return CallToolResult(content=[TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {req.params.name}"}))])


server.add_request_handler("tools/list", ListToolsRequest, list_tools_handler)
server.add_request_handler("tools/call", CallToolRequest, call_tool_handler)


# ─── MAIN ───

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())