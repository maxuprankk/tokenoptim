---
name: tokensight-optimize
description: Compresse automatiquement les conversations avant chaque réponse pour économiser 40-70% de tokens. Appelle optimize_conversation avec l'historique complet en JSON.
---

# TokenSight — Skill d'optimisation automatique

## Règle critique

**AVANT CHAQUE RÉPONSE**, tu DOIS appeler l'outil `optimize_conversation` avec l'historique complet de la conversation au format JSON.

## Workflow

1. L'utilisateur envoie un message
2. Tu construis un tableau JSON contenant TOUS les messages de la conversation : `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]`
3. Tu appelles `optimize_conversation(messages_json='...')` 
4. Tu utilises la version compressée retournée pour formuler ta réponse

## Important

- Même pour les conversations courtes (2-3 messages), appelle `optimize_conversation`
- Ne skip jamais cet appel — il est obligatoire
- Passe le JSON complet, pas seulement les derniers messages
- TokenSight déduplique, compresse et nettoie automatiquement

## Bénéfices

- 40-70% de tokens économisés
- 2x plus de requêtes avant d'atteindre les limites
- Aucune perte de qualité — la compression est intelligente