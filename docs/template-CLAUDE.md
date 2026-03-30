# CLAUDE.md — {{NOM DU PROJET}}

<!-- template-version: v1.1 -->

Fichier de référence lu à chaque session. Contient les préférences du projet et l'index de la documentation.

---

## 🚫 Règles absolues — Sécurité (inaltérables)

### NE JAMAIS publier de données sensibles
NE JAMAIS mentionner, copier, suggérer ou inclure :
- Mots de passe
- Clés API / Tokens (OpenAI, AWS, Anthropic, etc.)
- Jetons d'authentification
- Identifiants secrets (`.env`, `secrets.json`, etc.)

**AVANT TOUT COMMIT** : vérifier systématiquement l'absence de secrets.
Toute suggestion de code contenant des secrets = ERREUR CRITIQUE IMMÉDIATE.

### NE JAMAIS commiter de fichiers .env
- `.env`, `.env.local`, `.env.*` → **TOUJOURS** dans `.gitignore`
- Claude lit automatiquement ces fichiers → risque d'exposition
- Vérification obligatoire : `git diff --cached | grep -i env`

### ✅ Ce que Claude doit faire
- Toujours suggérer : `echo ".env" >> .gitignore`
- Toujours détecter les secrets dans le code avant suggestion
- Toujours proposer des variables d'environnement génériques :

```bash
# ❌ MAUVAIS
API_KEY=sk-123456

# ✅ BON
API_KEY=${API_KEY}
```

- Toujours rappeler cette règle en début de session

---

## Préférences générales

- **Commits Git** : ne jamais inclure `Co-Authored-By: Claude...` dans les messages de commit.
- **Langue** : répondre en français. Docstrings et commentaires de code en anglais.
- **Fuseau horaire** : Europe/Paris
- **Ne jamais produire de code sans demande explicite.** Privilégier d'abord la compréhension conceptuelle.

---

## Standards de code

- **Principes** : DRY (Don't Repeat Yourself), KISS (Keep It Simple Stupid), Clean Code.
- **Approche** : développement itératif avec étapes progressives et testables.
- **Tests** : approche TDD quand approprié (pytest pour Python).
- **Commits** : messages en anglais, format conventionnel :

```
feat: add user authentication
fix: correct null pointer in data parser
docs: update API usage in README
refactor: extract validation logic into helper
chore: update dependencies
```

---

## Structure de réponse attendue

- Résumé des objectifs en début de réponse (style TL;DR) pour les sujets complexes.
- Explications en prose claire, sans listes à puces excessives.
- Citations des sources pertinentes avec liens quand disponibles.
- Proposer du code uniquement si demandé explicitement.

---

## Workflow de collaboration

- **réflexion** : on discute stratégie avant de faire.
- **go** : validation explicite reçue ("go", "exécute", "c'est bon"). Claude implémente.
- **Modification du CLAUDE.md** : toujours présenter un avant/après sur les sections concernées. Ne jamais modifier sans validation explicite.

---

## Workflow Git

- **Ne jamais produire de code sans accord préalable.** Proposer une stratégie, attendre la validation, puis implémenter.
- **Branches de code** : tout fichier de code doit transiter par une feature branch.
- **Documentation** : peut être commitée directement sur `{{staging}}`.
- **Une branche par feature/tâche.** Plusieurs correctifs liés peuvent être regroupés.
- Flux : `feature-branch` → `{{staging}}` → `main` → `{{prod}}`

### Conventions de nommage des branches

```
feat/{{description}}       # nouvelle fonctionnalité
fix/{{description}}        # correction de bug
docs/{{description}}       # documentation uniquement
refactor/{{description}}   # refactorisation sans changement fonctionnel
chore/{{description}}      # maintenance (dépendances, config)
```

### Branches actives

| Branche | Rôle | État |
|---------|------|------|
| `main` | Production | stable |
| `{{staging}}` | Staging / docs | actif |

---

## Workflow Tâches

- Tâches suivies sur **Nextcloud**, liste `{{NOM DE LA LISTE}}`
- Début de session : lire les tâches ouvertes
- Fin de session : actualiser Nextcloud (nouvelles tâches + tâches terminées)

---

## Contexte projet

- **Nom** : {{NOM DU PROJET}}
- **Type** : {{site vitrine / app web / outil CLI / lib / autre}}
- **Objectif** : {{description en une phrase}}
- **Stack technique** : {{langages, frameworks, outils principaux}}
- **Repo** : {{user}}/{{repo}}
- **Branche principale** : main
- **Déploiement** : {{URL ou plateforme}}

### Structure clé

```
{{répertoire}}    # {{rôle}}
{{répertoire}}    # {{rôle}}
{{fichier}}       # {{rôle}}
```

---

## Documentation du projet

| Fichier | Rôle | Mettre à jour quand |
|---------|------|---------------------|
| `CLAUDE.md` | Référence session IA | À chaque changement structurel |
| `README.md` | Vue d'ensemble projet | Changement de structure ou déploiement |
| `{{AUTRE.md}}` | {{rôle}} | {{quand}} |

**Règle** : la documentation se met à jour avant le merge `{{staging}}` → `main`, jamais après.

---

## Notes spécifiques au projet

{{Section libre : contraintes techniques, historique de décisions, points d'attention particuliers.}}

---

## Changelog template

| Version | Description |
|---------|-------------|
| v1.1 | Ajout versionning sémantique (template-version + changelog) |
| v1.0 | Version initiale |
