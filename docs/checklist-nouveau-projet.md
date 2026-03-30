# Checklist — Initialisation d'un nouveau projet

<!-- template-version: v1.1 -->

À exécuter dans l'ordre au démarrage de tout nouveau projet collaboratif avec Claude.

---

## Étape 1 — Git

- [ ] `git init` ou clone du repo existant
- [ ] Vérifier que `.gitignore` contient : `.env`, `.env.*`, `*.local`
- [ ] Créer la branche staging : `git checkout -b actualisation` (ou équivalent)
- [ ] Définir la convention de nommage des branches (feat/, fix/, docs/, chore/)
- [ ] Premier commit : structure de base + `.gitignore`

## Étape 2 — CLAUDE.md

- [ ] Copier `docs/template-CLAUDE.md` à la racine du projet
- [ ] Renommer en `CLAUDE.md`
- [ ] Remplir tous les `{{placeholders}}` :
  - Nom du projet
  - Type et objectif
  - Stack technique
  - Repo et URL de déploiement
  - Structure clé (répertoires et fichiers principaux)
  - Branches (staging, prod)
  - Liste Nextcloud
- [ ] Supprimer les sections non applicables
- [ ] Noter la version du template utilisée (visible en en-tête : `<!-- template-version: vX.X -->`)
- [ ] Commiter sur staging : `git add CLAUDE.md && git commit -m "init: CLAUDE.md"`

## Étape 3 — Nextcloud

- [ ] Créer une liste dédiée au projet dans Nextcloud Tasks
- [ ] Nommer la liste identiquement au projet (ex: `Aboriginal Way`, `MonProjet`)
- [ ] Ajouter une première tâche : "Initialisation projet"
- [ ] Mettre le nom de la liste dans le CLAUDE.md (section Workflow Tâches)

## Étape 4 — Documentation minimale

- [ ] Créer `README.md` (description, stack, instructions d'installation)
- [ ] Créer `docs/` si le projet a des fichiers de documentation
- [ ] Référencer les fichiers doc dans la table du CLAUDE.md

## Étape 5 — Première session Claude

- [ ] Ouvrir Claude Code dans le répertoire du projet
- [ ] Vérifier que CLAUDE.md est bien lu (demander : "montre le contenu de CLAUDE.md")
- [ ] Lire les tâches Nextcloud ouvertes
- [ ] Valider le contexte avec Claude avant de commencer le travail

---

## Rappel — Ce que cette organisation apporte

| Problème évité | Mécanisme |
|---------------|-----------|
| Claude qui "oublie" le contexte | CLAUDE.md lu à chaque session |
| Préférences à répéter | Mémoire auto par projet |
| Tâches perdues entre sessions | Nextcloud (externe à Git et Claude) |
| Code commité sans validation | Protocole réflexion / go |
| Secrets exposés | Règles absolues sécurité dans CLAUDE.md |
| Branches qui partent dans tous les sens | Convention de nommage + flux défini |
| Version du template inconnue | `<!-- template-version -->` en en-tête |

---

## Signaux que l'organisation fonctionne

- Tu ne répètes pas deux fois la même préférence à Claude
- Tu sais à tout moment quelle branche est active et pourquoi
- Les tâches Nextcloud reflètent l'état réel du projet
- Claude propose avant de faire
- La version du template est traçable dans chaque projet

---

## Changelog checklist

| Version | Description |
|---------|-------------|
| v1.1 | Ajout versionning sémantique (template-version + changelog) |
| v1.0 | Version initiale |
