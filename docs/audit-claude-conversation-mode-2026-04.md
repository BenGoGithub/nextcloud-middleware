# Audit — Mode conversationnel Claude → Nextcloud
*Rédigé le 2026-04-02 — branche `claude/review-claude-md-GO1fP`*

---

## 1. État actuel du middleware

### Endpoints existants

| Endpoint | Rôle |
|---|---|
| `GET /health` | Santé du service |
| `POST /task` | Texte libre → tâche CalDAV ou carte Deck |
| `POST /task/confirm` | Confirmation d'une clarification en attente |
| `POST /event` | Texte libre → événement calendrier |
| `POST /event/confirm` | Confirmation d'une clarification en attente |

### Flux actuel (`POST /task`)

```
[Texte brut]
     ↓
[LLM — messages.parse() → TaskOutput structuré]
     ↓ confidence < 0.7 ?
     → ClarificationResponse (options + request_id)
     ↓ confidence ≥ 0.7
[router.dispatch()]
     ├─ target_type=task → adapters/tasks.py (CalDAV)
     └─ target_type=deck → adapters/deck.py (Deck REST API)
```

### Points forts constatés

- **Adapters solides** : CalDAV (`caldav_tasks_api`) et Deck (httpx + TTLCache) bien séparés.
- **Gestion de la confiance** : mécanisme de clarification en mémoire (TTL 10 min) via `PendingConfirmationStore`.
- **Retry LLM** : tenacity (3 essais, backoff exponentiel 1–4 s).
- **Sécurité** : Bearer token sur tous les endpoints écriture.
- **Modèle configurable** : `anthropic_model` dans `.env`, actuellement `claude-sonnet-4-6`.

### Limites actuelles (au regard de la nouvelle approche)

| Limite | Impact |
|---|---|
| LLM **one-shot** — aucun historique de conversation | Pas de dialogue, pas de correction progressive |
| `TaskRequest` n'accepte que `text: str` | Impossible de passer un contexte enrichi |
| Pas de mode **batch** | Une requête = une tâche |
| Pas de lecture/liste des tâches existantes | Impossible de vérifier les doublons |
| Clarification limitée aux **alternatives de parsing** | Pas de vrai dialogue sémantique |

---

## 2. Nouvelle approche — Architecture cible

### Principe de séparation

```
┌─────────────────────────────────────────────┐
│  CLAUDE (conversation ici)                  │
│  • Intelligence, tri, priorisation          │
│  • Dialogue naturel pour compléter les infos│
│  • Détection de doublons / cohérence        │
│  • Validation explicite avant action        │
│  • Mémoire de session (fichier repo)        │
└───────────────────┬─────────────────────────┘
                    │ POST /task ou /event
                    │ (texte déjà propre et complet)
┌───────────────────▼─────────────────────────┐
│  MIDDLEWARE VPS                             │
│  • Parsing structuré final (LLM)            │
│  • Dispatch CalDAV / Deck                   │
│  • Gestion credentials Nextcloud            │
│  • Retry, cache, erreurs techniques         │
└─────────────────────────────────────────────┘
```

### Ce qui ne change pas côté VPS

- Les adapters CalDAV et Deck restent intacts.
- L'authentification Bearer token reste en place.
- La logique de retry et de cache TTL reste en place.

### Ce qui change (ou est à discuter)

Voir section 3 — Questions ouvertes.

---

## 3. Questions ouvertes

### Q1 — Double appel LLM : à optimiser ou à accepter ?

**Contexte** : Dans la nouvelle approche, Claude (ici) fait déjà tout le travail sémantique.
Quand il appelle `POST /task`, le middleware déclenche un second appel LLM (`messages.parse()`)
pour re-parser le texte en `TaskOutput`.

**Option A — Accepter le double appel**
Avantage : zéro modification du middleware, séparation nette.
Inconvénient : latence légèrement augmentée, coût API doublé sur la partie parsing.

**Option B — Nouveau endpoint `POST /task/structured`**
Claude envoie directement un `TaskOutput` JSON complet, le middleware saute l'appel LLM
et dispatch directement.
Avantage : efficacité maximale, cohérence garantie.
Inconvénient : modification du middleware + Claude doit construire le JSON lui-même.

> **À valider** : option A ou B ?

---

### Q2 — Stockage session dans le repo : format et périmètre

**Objectif** : me permettre de garder le fil entre sessions (tâches en attente, contexte projet,
décisions prises).

**Proposition** : un dossier `session/` avec :
- `session/context.md` — notes libres sur le contexte en cours
- `session/pending.json` — tâches discutées mais pas encore créées (si validation différée)

**Questions** :
- Ce dossier doit-il être committé sur la branche de travail, ou ignoré (`.gitignore`) ?
- Faut-il une rotation / archivage des entrées passées ?

> **À valider** : périmètre et format du stockage.

---

### Q3 — Authentification : comment je transmets le token API ?

**Contexte** : pour appeler `POST /task`, j'ai besoin du Bearer token défini dans `.env`
sur le VPS (`api_token`). Ce token ne doit jamais être committé.

**Options** :
- Tu me le passes oralement en début de session (je ne le stocke pas).
- On crée un `.env.local` non commité côté repo local de cette instance.
- On ajoute un endpoint `GET /health` étendu sans auth pour valider la connectivité,
  et le token reste dans la session uniquement.

> **À valider** : mode de transmission du token.

---

### Q4 — Batch : plusieurs tâches en une conversation

**Contexte** : il peut arriver que tu mentionnes plusieurs choses à créer en une phrase
("pense à rappeler le dentiste et à finir le devis Aboriginal Way").

**Option A** : je les envoie une par une (deux appels `POST /task`).
Simple, pas de modification middleware.

**Option B** : nouveau endpoint `POST /tasks` (pluriel) acceptant une liste.
Nécessite modification middleware et adapter.

> **À valider** : est-ce un besoin fréquent ? Option A suffisante pour commencer ?

---

### Q5 — Périmètre de mon rôle : uniquement créer ou aussi lire ?

**Contexte** : pour détecter les doublons ou vérifier ce qui existe, je devrais pouvoir
lire les tâches existantes dans Nextcloud.

Aujourd'hui le middleware ne propose aucun endpoint de lecture.

**Option A** : je ne lis pas — je gère la cohérence uniquement via la mémoire de session.
Simple, aucun développement.

**Option B** : ajout d'un `GET /tasks?list=Inbox` sur le middleware.
Permet une vraie vérification des doublons, mais représente un chantier distinct.

> **À valider** : est-ce nécessaire dans un premier temps, ou on commence sans ?

---

## 4. Proposition de séquençage

Si on valide les options simples (A partout pour commencer) :

| Étape | Contenu | Effort |
|---|---|---|
| **0 — Aujourd'hui** | Valider les réponses aux 5 questions ci-dessus | — |
| **1 — Connexion** | Tester un appel `POST /task` depuis cette session | Nul côté code |
| **2 — Session storage** | Créer `session/context.md` et `session/pending.json` | Faible |
| **3 — Batch simple** | Je gère le multi-tâche en N appels successifs | Nul côté code |
| **4 — Endpoint structured** | Si Q1 → option B, ajouter `POST /task/structured` | Moyen |
| **5 — Lecture tâches** | Si Q5 → option B, ajouter `GET /tasks` | Moyen |

---

## 5. Résumé des décisions à prendre

| # | Question | Options |
|---|---|---|
| Q1 | Double appel LLM | A — accepter / B — endpoint structuré |
| Q2 | Stockage session | Format + commité ou ignoré ? |
| Q3 | Token API | Session orale / .env.local / autre |
| Q4 | Batch | A — appels successifs / B — endpoint liste |
| Q5 | Lecture tâches | A — mémoire session / B — GET /tasks |
