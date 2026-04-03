# Architecture Decision Records — nextcloud-middleware

*Projet : nextcloud-middleware · Production : https://middleware.aboriginalway.fr*  
*Rédigé le 2026-04-03 · Format : ADR (Architecture Decision Record)*

---

## Sommaire

| ID | Titre | Statut |
|---|---|---|
| ADR-001 | Endpoint dédié `POST /task/structured` | ✅ Décidé |
| ADR-002 | Stockage session en fichiers plats | ✅ Décidé |
| ADR-003 | Gestion du batch par appels successifs | ✅ Décidé |
| ADR-004 | Pas de lecture Nextcloud en V1 | ✅ Décidé |
| ADR-005 | Coexistence `TaskOutput` et `StructuredTaskInput` | ✅ Décidé |

---

## Contexte général

Le middleware `nextcloud-middleware` est un service FastAPI déployé sur VPS Scaleway (Ubuntu 24.04).
Il reçoit des requêtes en langage naturel, les route via un LLM (Claude Haiku) vers Nextcloud Tasks (CalDAV) ou Nextcloud Deck (REST API).

À partir d'avril 2026, l'architecture évolue vers un mode conversationnel où Claude (claude.ai) joue le rôle de couche sémantique amont. Cette évolution modifie le contrat d'entrée du middleware et justifie les décisions documentées ci-dessous.

### Schéma d'architecture cible

```
┌─────────────────────────────────────────────┐
│  CLAUDE (conversation claude.ai)            │
│  • Intelligence sémantique                  │
│  • Dialogue et clarification                │
│  • Validation explicite avant action        │
│  • Mémoire de session (fichiers locaux)     │
└───────────────────┬─────────────────────────┘
                    │ POST /task/structured
                    │ (objet JSON typé et validé)
┌───────────────────▼─────────────────────────┐
│  MIDDLEWARE VPS (FastAPI)                   │
│  • Validation Pydantic                      │
│  • Routage déterministe CalDAV / Deck       │
│  • Gestion credentials Nextcloud            │
│  • Retry, cache, erreurs techniques         │
└─────────────────────────────────────────────┘
```

---

## ADR-001 — Endpoint dédié `POST /task/structured`

**Date** : 2026-04-03  
**Statut** : Décidé  
**Décideur** : Ben (architecture) + Claude.ai (analyse)

### Contexte

Dans l'architecture initiale, `POST /task` reçoit du texte brut et déclenche un appel LLM interne (`messages.parse()`) pour produire un `TaskOutput` structuré. Avec Claude comme couche sémantique amont, ce second appel LLM devient redondant : Claude a déjà fait le travail d'extraction d'intention et de structuration.

La question est donc : faut-il modifier `POST /task` pour accepter les deux formats, ou créer un endpoint dédié ?

### Options évaluées

| Critère | Option A — Double appel LLM accepté | Option B — `POST /task/structured` dédié |
|---|---|---|
| Modification du middleware | Aucune | Ajout d'un endpoint |
| Coût API | Doublé sur la partie parsing | Un seul appel LLM |
| Latence | Augmentée (~300–600 ms) | Réduite |
| Risque d'interprétation divergente | Élevé : deux LLM peuvent diverger | Nul : Claude construit le JSON final |
| Clarté du contrat d'interface | Faible : l'endpoint fait "tout" | Forte : responsabilités explicites |
| Maintenabilité | Couplage implicite | Séparation nette des couches |
| Alignement tendances 2026 | Pattern en recul | Pattern mainstream (structured output natif) |

### Décision

**Option B retenue.** Le structured output natif est le pattern consolidé en 2026 chez les principaux fournisseurs LLM (Anthropic, OpenAI, Gemini, Mistral). La divergence d'interprétation entre deux appels LLM successifs est un risque architectural plus sérieux que le coût de maintenance d'un endpoint supplémentaire. `POST /task` existant est conservé intact pour la compatibilité.

### Conséquences

- Créer `POST /task/structured` dans `middleware/routers/tasks.py`
- Définir le schéma `StructuredTaskInput` (Pydantic v2)
- Le dispatch CalDAV / Deck reste inchangé
- `POST /task` continue de fonctionner pour les appels directs sans Claude

---

## ADR-002 — Stockage session en fichiers plats

**Date** : 2026-04-03  
**Statut** : Décidé  
**Décideur** : Ben

### Contexte

Pour maintenir une continuité entre sessions conversationnelles (tâches en attente, contexte projet, décisions prises), un mécanisme de persistance léger est nécessaire côté Claude. La question porte sur le format et l'infrastructure de ce stockage.

### Options évaluées

| Critère | Fichiers plats (Markdown / JSON) | Vector store / backend mémoire |
|---|---|---|
| Complexité opérationnelle | Nulle | Élevée (infra dédiée) |
| Lisibilité humaine | Totale | Opaque |
| Auditabilité / debug | Facile | Difficile |
| Recherche sémantique | Non disponible | Disponible |
| Pertinence à l'échelle | Limitée (fichier volumineux = dégradation) | Adaptée aux grands volumes |
| Adéquation usage personnel | Très bonne | Sur-dimensionné |
| Coût | Nul | Variable selon solution |

### Décision

**Fichiers plats retenus**, stockés hors Git (entrées dans `.gitignore`).

Structure retenue :
```
session/
├── context.md       # Notes libres sur le contexte en cours
└── pending.json     # Tâches discutées, pas encore créées
```

Le vector store est un sur-dimensionnement pour un usage mono-utilisateur à faible volume. La limite de taille du fichier est gérée par discipline de nettoyage manuel entre sessions.

### Conséquences

- Créer `session/` à la racine du repo
- Ajouter `session/` dans `.gitignore`
- Documenter la convention de nettoyage dans `CLAUDE.md`

---

## ADR-003 — Gestion du batch par appels successifs

**Date** : 2026-04-03  
**Statut** : Décidé  
**Décideur** : Ben

### Contexte

Il arrive qu'un utilisateur mentionne plusieurs tâches dans une même phrase ("rappelle-moi d'appeler le dentiste et de finir le devis"). Faut-il gérer ce cas côté middleware (endpoint batch) ou côté Claude (N appels successifs) ?

### Options évaluées

| Critère | Option A — Appels successifs | Option B — `POST /tasks` (liste) |
|---|---|---|
| Modification middleware | Aucune | Chantier non négligeable |
| Isolation des erreurs | Bonne : chaque tâche est indépendante | Complexe : erreurs partielles à gérer |
| Latence pour N tâches | Cumulée (N × latence unitaire) | Réduite (1 round-trip) |
| Atomicité | Non garantie | Possible |
| Fréquence du cas N > 3 | Rare dans l'usage réel | — |
| Complexité implémentation | Nulle | Moyenne à élevée |

### Décision

**Option A retenue pour la V1.** Le cas de 3+ tâches simultanées est rare. L'isolation des erreurs par appel est un avantage concret. L'Option B est documentée comme évolution possible en V2 si le besoin émerge.

### Conséquences

- Aucune modification middleware
- Claude gère le multi-tâche en N appels `POST /task/structured` successifs
- Évolution Option B tracée dans la roadmap

---

## ADR-004 — Pas de lecture Nextcloud en V1

**Date** : 2026-04-03  
**Statut** : Décidé  
**Décideur** : Ben

### Contexte

Pour détecter les doublons ou vérifier l'état des tâches existantes, il faudrait un endpoint de lecture côté middleware (`GET /tasks`). Actuellement, aucun endpoint de lecture n'existe.

### Options évaluées

| Critère | Option A — Mémoire session seule | Option B — `GET /tasks` middleware |
|---|---|---|
| Développement requis | Aucun | Chantier distinct |
| Détection doublons | Partielle (inter-sessions : non couverte) | Fiable |
| Robustesse inter-sessions | Faible si session perdue | Forte |
| Exposition de données | Aucune | Surface d'attaque supplémentaire |
| Pertinence à faible volume | Suffisante | Sur-dimensionné |

### Décision

**Option A retenue en V1.** À faible volume d'usage, le risque de doublon est acceptable. La mémoire de session (`session/pending.json`) couvre les cas les plus courants. L'Option B est tracée comme évolution Phase E dans la roadmap.

### Conséquences

- Aucune modification middleware
- Les doublons inter-sessions sont un risque accepté et documenté
- Évolution `GET /tasks` tracée dans la roadmap

---

## ADR-005 — Coexistence `TaskOutput` et `StructuredTaskInput`

**Date** : 2026-04-03  
**Statut** : Décidé  
**Décideur** : Ben

### Contexte

`TaskOutput` est le schéma Pydantic existant utilisé par `POST /task` pour le parsing LLM interne. `StructuredTaskInput` est le nouveau schéma enrichi pour `POST /task/structured`. Faut-il fusionner les deux ou les faire coexister ?

### Options évaluées

| Critère | Fusionner en un seul schéma | Coexistence des deux schémas |
|---|---|---|
| Rétrocompatibilité `POST /task` | Risquée | Garantie |
| Clarté des contrats | Moins bonne (schéma surchargé) | Meilleure (responsabilités séparées) |
| Surface de régression | Élevée | Faible |
| Maintenabilité long terme | Schéma unique à maintenir | Deux schémas à synchroniser |

### Décision

**Coexistence retenue.** `TaskOutput` reste inchangé pour `POST /task`. `StructuredTaskInput` est un nouveau schéma dédié à `POST /task/structured`, avec des champs supplémentaires (`timezone`, `intent`, `target_system`). Une factorisation partielle (classe de base commune) est possible en V2 si la divergence devient problématique.

### Champs de `StructuredTaskInput` (V1)

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `intent` | `str` | ✅ | Type d'action : `create_task`, `create_event` |
| `target_system` | `str` | ✅ | `caldav` ou `deck` |
| `title` | `str` | ✅ | Titre de la tâche ou de l'événement |
| `description` | `str` | ❌ | Description libre |
| `due_at` | `datetime` | ❌ | Échéance |
| `start_at` | `datetime` | ❌ | Début (événements) |
| `timezone` | `str` | ❌ | Ex. `Europe/Paris` — défaut UTC |
| `labels` | `list[str]` | ❌ | Étiquettes |
| `board_id` | `int` | ❌ | Obligatoire si `target_system=deck` |
| `stack_id` | `int` | ❌ | Obligatoire si `target_system=deck` |
| `calendar_id` | `str` | ❌ | Obligatoire si `target_system=caldav` |
| `confidence` | `float` | ❌ | Score 0–1, informatif |

### Conséquences

- Créer `StructuredTaskInput` dans `middleware/schemas.py`
- `TaskOutput` reste inchangé
- Factorisation possible en V2

---

## Références

- [python-caldav documentation](https://python-caldav.readthedocs.io/)
- [Nextcloud Deck API](https://deck.readthedocs.io/en/latest/API/)
- [RFC 4791 — CalDAV](https://datatracker.ietf.org/doc/html/rfc4791)
- [RFC 5545 — iCalendar](https://datatracker.ietf.org/doc/html/rfc5545)
- [Nextcloud issue #45333 — VTODO CalDAV](https://github.com/nextcloud/server/issues/45333)
- Audit interne : `audit-nextcloud-middleware.md` (2026-04-02)

---

*Document généré par Claude.ai · Projet nextcloud-middleware · Avril 2026*
