# nextcloud-middleware — CLAUDE.md

<!-- template-version: v1.3 -->

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
- Doc et code ne sont jamais mixés dans le même commit. Une PR peut contenir les deux.
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
- **Ne jamais supprimer `main`** — branche structurelle, intacte en toutes circonstances.
- **Doc et code séparés** : jamais dans le même commit. Une PR peut contenir les deux.

### Flux par instance

```
Claude Code JetBrains
feat/* | fix/* | refactor/* | chore/*  →  main  (PR, merge par Ben)

Claude Code VPS
claude/doc-{{description}}  →  main  (commits doc uniquement)
claude/{{description}}      →  main  (commits code uniquement)
```

### Conventions de nommage des branches

```
feat/{{description}}       # nouvelle fonctionnalité
fix/{{description}}        # correction de bug
docs/{{description}}       # documentation uniquement
refactor/{{description}}   # refactorisation sans changement fonctionnel
chore/{{description}}      # maintenance (dépendances, config)
claude/doc-{{description}} # branche VPS — commits doc
claude/{{description}}     # branche VPS — commits code
```

### Branches structurelles

| Branche | Rôle | Propriétaire | État |
|---------|------|--------------|------|
| `main` | Production | Ben | stable — ne jamais supprimer |

---

## Workflow Tâches

- **Backlog technique** (bugs, features, refacto) : GitHub Issues du repo.
- **Décisions stratégiques** (architecture, intégrations, évolutions système) : Nextcloud, liste `Productivity`.
- Début de session : consulter les Issues ouvertes + tâches Productivity en cours.
- Fin de session : mettre à jour Issues (statut) et Productivity si décision prise.

---

## Contexte projet

- **Nom** : nextcloud-middleware
- **Type** : service API (middleware)
- **Objectif** : recevoir une phrase en langage naturel et créer une tâche Nextcloud Tasks (CalDAV), une carte Nextcloud Deck, ou un événement calendrier (VEVENT) selon le contexte détecté.
- **Stack** : Python 3.12, FastAPI + Uvicorn, Pydantic v2, anthropic SDK, caldav-tasks-api, httpx, tenacity, cachetools
- **Repo** : BenGoGithub/nextcloud-middleware
- **Branche principale** : main
- **Déploiement** : https://middleware.aboriginalway.fr (VPS Scaleway Berlin, systemd + Nginx + HTTPS)

### Structure clé

```
middleware/main.py              # FastAPI app — POST /task, POST /event, GET /health
middleware/llm.py               # call_llm() + call_llm_event() — messages.parse() + tenacity retries
middleware/prompt.py            # system prompts + ROUTING_RULES + build_event_system_prompt()
middleware/router.py            # dispatches TaskOutput to task or deck adapter
middleware/adapters/tasks.py    # CalDAV VTODO creation + _create_vevent() (RFC 5545)
middleware/adapters/deck.py     # Deck card creation (2-step POST+PUT for duedate)
middleware/adapters/events.py   # CalDAV VEVENT creation — _find_vevent_calendar()
middleware/models.py            # TaskOutput, EventOutput, TaskRequest, EventResponse, confidence
middleware/config.py            # pydantic-settings from .env
```

---

## Notes techniques

### Endpoints disponibles

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/health` | GET | Aucune | Liveness check — `{"status": "ok"}` |
| `/task` | POST | Bearer | Crée un VTODO ou une carte Deck via routing LLM |
| `/event` | POST | Bearer | Crée un VEVENT dans le calendrier CalDAV |

### LLM call
Utiliser `client.messages.parse()` (pas `client.messages.create`) dans `middleware/llm.py`
pour bénéficier de la validation Pydantic native sur le structured output.

### Routing keyword rules
Source de vérité : `TASK_ROUTING.md` dans le repo Productivity.
La constante `ROUTING_RULES` dans `middleware/prompt.py` doit rester synchronisée.

Active Deck board : **Aboriginal Way** (uniquement).
SNALE n'est pas un board Deck — les tâches SNALE vont dans Nextcloud Tasks (CalDAV).

### VEVENT — points d'attention
- `_find_vevent_calendar()` cible le **premier** calendrier VEVENT-capable trouvé sur le principal CalDAV.
- `CALDAV_DEFAULT_CALENDAR` ou un champ `calendar` sur `EventOutput` permettrait de cibler un calendrier précis — **décision en suspens**.
- Les collections VTODO (Nextcloud Tasks) rejettent les VEVENT — ne pas cibler une liste de tâches.

### Confidence — décision en suspens
- `confidence: float = 1.0` est retourné dans `TaskResponse` et `EventResponse`.
- Le flow `confidence < 0.7` → `202 clarification_needed` n'est **pas implémenté**.
- Décision requise avant implémentation : seuil, second appel LLM ou template statique, gestion côté client.

### Gestion des erreurs
- `ValueError` (liste inconnue, board Deck inconnu) → HTTP 400
- `httpx.HTTPStatusError` (Deck API indisponible) → HTTP 502

### Deck API notes
- Board/stack IDs sont cachés (TTLCache, 1h). Cache invalidé sur 404.
- Due date requiert une seconde requête PUT (upstream issue #4106).
- Headers requis : `OCS-APIRequest: true`, `Authorization: Basic`.

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

**Règle** : la documentation se met à jour dans la même PR que le code, jamais après le merge.

---

## Changelog CLAUDE.md

| Version | Description |
|---------|-------------|
| v1.3 | Gouvernance : branche par instance, flux PR doc/code séparés (commits distincts, PR possible), règle nettoyage branches, action corrective VPS sur main. Workflow tâches : GitHub Issues + Productivity. Stack : /event, EventOutput, confidence, /health, gestion exceptions. |
| v1.2 | Ajout section gouvernance instances Claude |
| v1.1 | Alignement template v1.1 — ajout sécurité, préférences, workflows, table docs |
| v1.0 | Version initiale (technique uniquement) |
