# nextcloud-middleware — CLAUDE.md

<!-- template-version: v1.1 -->

Fichier de référence lu à chaque session. Contient les préférences du projet et l'index de la documentation.

---

## 🚫 Règles absolues — Sécurité (inaltérables)

### NE JAMAIS publier de données sensibles
NE JAMAIS mentionner, copier, suggérer ou inclure :
- Mots de passe
- Clés API / Tokens (Anthropic, etc.)
- Jetons d'authentification
- Identifiants secrets (`.env`, `secrets.json`, etc.)

**AVANT TOUT COMMIT** : vérifier systématiquement l'absence de secrets.
Toute suggestion de code contenant des secrets = ERREUR CRITIQUE IMMÉDIATE.

### NE JAMAIS commiter de fichiers .env
- `.env`, `.env.local`, `.env.*` → **TOUJOURS** dans `.gitignore`
- Claude lit automatiquement ces fichiers → risque d'exposition
- Vérification obligatoire : `git diff --cached | grep -i env`

---

## Préférences générales

- **Commits Git** : ne jamais inclure `Co-Authored-By: Claude...` dans les messages de commit.
- **Langue** : répondre en français. Docstrings, commentaires et commits en anglais.
- **Fuseau horaire** : Europe/Paris
- **Ne jamais produire de code sans demande explicite.** Privilégier d'abord la compréhension conceptuelle.

---

## Standards de code

- **Principes** : DRY, KISS, Clean Code.
- **Approche** : développement itératif avec étapes progressives et testables.
- **Tests** : pytest (approche TDD quand approprié).
- **Commits** : messages en anglais, format conventionnel (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).

---

## Workflow de collaboration

- **réflexion** : on discute stratégie avant de faire.
- **go** : validation explicite reçue. Claude implémente.
- **Modification du CLAUDE.md** : toujours présenter un avant/après sur les sections concernées. Ne jamais modifier sans validation explicite.

---

## Instances Claude — gouvernance

Ce projet est servi par trois instances Claude aux rôles distincts.

| Instance | Contexte | Branche de travail | Périmètre |
|---|---|---|---|
| **Claude.ai** | Navigateur (claude.ai) | — | Architecture, docs, décisions structurelles |
| **Claude Code — JetBrains** | Poste local Ben-Wedo | `feat/*`, `fix/*` | Génération code, commits locaux, ouverture PR |
| **Claude Code — VPS** | claude-ops@168.222.244.80 | `claude/*` | Fixes runtime, doc, ouverture PR vers main |

### Règles non négociables

- Claude Code (JetBrains ou VPS) peut ouvrir une PR vers `main` — jamais la merger.
- Claude Code VPS travaille exclusivement sur des branches `claude/*`.
- Doc et code ne doivent jamais être dans le même commit. Ils peuvent coexister dans la même PR à condition que chaque commit soit atomique.
- Ben relit le diff et merge toutes les PR.
- Ben supprime les branches mergées (localement et sur origin). Claude Code ne supprime jamais de branches.
- Toute opération système (apt, systemd, nginx) → root SSH uniquement, hors périmètre Claude Code.

### Vérifications début de session (Claude Code VPS)
```bash
git branch --show-current          # doit être claude/* — jamais main
                                   # si sur main : git checkout -b claude/{{description}} avant toute modification
git config --local user.name       # claude-ops
echo ${ANTHROPIC_API_KEY:-absent}  # doit retourner "absent"
systemctl status nextcloud-middleware
```

---

## Workflow Git

- **Une branche par PR, une PR par sujet.**
- **Ne jamais supprimer les branches structurelles** : `main`. Intacte en toutes circonstances.
- **Doc et code séparés** : doc et code ne doivent jamais être dans le même commit. Ils peuvent coexister dans la même PR à condition que chaque commit soit atomique (un commit doc, un commit code).

### Flux par instance

```
Claude Code JetBrains
feat/* | fix/* | refactor/* | chore/*  →  main  (PR, merge par Ben)

Claude Code VPS
claude/doc-{{description}}  →  main  (PR doc uniquement)
claude/{{description}}      →  main  (PR code uniquement)
```

### Conventions de nommage des branches

```
feat/{{description}}       # nouvelle fonctionnalité
fix/{{description}}        # correction de bug
docs/{{description}}       # documentation uniquement
refactor/{{description}}   # refactorisation sans changement fonctionnel
chore/{{description}}      # maintenance (dépendances, config)
claude/doc-{{description}} # PR doc VPS Claude Code
claude/{{description}}     # PR code VPS Claude Code
```

### Branches structurelles

| Branche | Rôle | Propriétaire | État |
|---------|------|--------------|------|
| `main` | Production | Ben | stable — ne jamais supprimer |

---

## Workflow Tâches

- Tâches suivies sur **Nextcloud**, liste `nextcloud-middleware`
- Début de session : lire les tâches ouvertes
- Fin de session : actualiser Nextcloud (nouvelles tâches + tâches terminées)

---

## Contexte projet

- **Nom** : nextcloud-middleware
- **Type** : service API (middleware)
- **Objectif** : recevoir une phrase en langage naturel et créer une tâche Nextcloud Tasks (CalDAV) ou une carte Nextcloud Deck selon le contexte détecté.
- **Stack** : Python 3.12, FastAPI + Uvicorn, Pydantic v2, anthropic SDK, caldav-tasks-api, httpx, tenacity, cachetools
- **Repo** : BenGoGithub/nextcloud-middleware
- **Branche principale** : main
- **Déploiement** : https://middleware.aboriginalway.fr (VPS Scaleway Berlin, systemd + Nginx + HTTPS)

### Structure clé

```
middleware/main.py             # FastAPI app, POST /task endpoint
middleware/llm.py              # LLM call (client.messages.parse()) + tenacity retries
middleware/prompt.py           # system prompt + ROUTING_RULES constant
middleware/router.py           # dispatches TaskOutput to task or deck adapter
middleware/adapters/tasks.py   # CalDAV task (and optional VEVENT) creation
middleware/adapters/deck.py    # Deck card creation (2-step PUT for duedate)
middleware/models.py           # TaskOutput, TaskRequest, TaskResponse
middleware/config.py           # pydantic-settings from .env
```

---

## Notes techniques

### LLM call
Use `client.messages.parse()` (not `client.messages.create`) in `middleware/llm.py`
to benefit from native Anthropic Pydantic validation on the structured output.

### Routing keyword rules
Source of truth: `TASK_ROUTING.md` in the Productivity repo.
The `ROUTING_RULES` constant in `middleware/prompt.py` must stay in sync with it.

Active Deck board: **Aboriginal Way** (only).
SNALE is NOT a Deck board — SNALE-related tasks go to Nextcloud Tasks (CalDAV).

### Deck API notes
- Board/stack IDs are cached (TTLCache, 1h). Cache is invalidated on 404.
- Due date requires a second PUT request (upstream issue #4106).
- Headers required: `OCS-APIRequest: true`, `Authorization: Basic`.

### Running locally
```
cp .env.example .env   # fill in credentials
pip install -r requirements.txt
uvicorn middleware.main:app --reload
```

---

## Documentation du projet

| Fichier | Rôle | Mettre à jour quand |
|---------|------|---------------------|
| `CLAUDE.md` | Référence session IA | À chaque changement structurel |
| `README.md` | Vue d'ensemble projet | Changement de structure ou déploiement |
| `docs/template-CLAUDE.md` | Template CLAUDE.md de référence | Évolution des standards |
| `docs/checklist-nouveau-projet.md` | Checklist d'initialisation | Évolution du processus |

**Règle** : la documentation se met à jour avant le merge `actualisation` → `main`, jamais après.

---

## Changelog CLAUDE.md

| Version | Description |
|---------|-------------|
| v1.3 | Gouvernance : branche de travail par instance, flux PR doc/code séparés, règle nettoyage branches |
| v1.2 | Ajout section gouvernance instances Claude |
| v1.1 | Alignement template v1.1 — ajout sécurité, préférences, workflows, table docs |
| v1.0 | Version initiale (technique uniquement) |
