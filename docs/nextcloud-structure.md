# Structure Nextcloud — Inventaire

_Dernière mise à jour : 2026-03-24_

Document vivant. À mettre à jour à chaque ajout ou suppression de liste / calendrier.

---

## Listes de tâches

| Liste | Domaine | État |
|-------|---------|------|
| `Productivity` | Suivi du projet Productivity (ce repo) | ✅ actif |
| `Aboriginal Way` | Projet dev personnel (hooks, PR, CI) | ✅ actif |
| `Alternance` | Alternance / CDA — travail et formation | ✅ actif |
| `Perso` | Vie personnelle, famille, projets, loisirs | ✅ actif |
| `Admin` | Démarches administratives, échéances | ✅ actif |
| `Veille` | Articles à lire, technologies à explorer | ✅ actif |
| `Santé` | Rendez-vous médicaux, objectifs fitness | ✅ actif |

---

## Calendriers

| Calendrier | Usage | Action |
|------------|-------|--------|
| `Personnel` | Événements vie perso | ✅ garder |
| `Aboriginal Way` | Événements liés au projet dev | ✅ garder |
| `Workout Rotator` | Planning sport / entraînements | ✅ garder |
| `Productivity` | Échéances de ce projet | ✅ garder |
| `Site AboriginalWay` | Usage à préciser | 🔲 à définir |
| `Anniversaires des contacts` | Généré automatiquement par Nextcloud | ✅ garder (auto) |
| `Tâches` | Généré automatiquement par Nextcloud Tasks | ✅ garder (auto) |
| `Deck: Bienvenue dans Nextcloud Deck !` | Calendrier par défaut de Deck, inutile | 🗑 à supprimer |

---

## Workflows session

### Début de session
1. `list_tasks` sur les listes actives → identifier les priorités du jour
2. `list_events` sur la période en cours → vérifier les échéances calendrier
3. Aligner tâches et calendrier si besoin

### Fin de session
1. `complete_task` pour chaque tâche terminée
2. `add_task` pour les nouvelles tâches identifiées
3. `add_event` si une deadline a été fixée pendant la session
4. Commit des fichiers modifiés si nécessaire

### Workflows à définir

- [ ] **Revue hebdomadaire** : priorisation des tâches, nettoyage des listes, planification calendrier
- [ ] **Liaison tâche ↔ événement** : quand une tâche a une deadline, créer l'événement correspondant
- [ ] **Tâches récurrentes** : définir quelles tâches sont récurrentes et à quelle fréquence
- [ ] **Archivage** : critères pour archiver ou supprimer une liste / un calendrier
- [ ] **Revue mensuelle** : bilan des domaines de vie, ajustement des priorités

---

## Notes

- Nextcloud auto-hébergé sur VPS, accessible 24h/24 depuis PC et Android
- Les listes et calendriers sont synchronisés automatiquement sur Android via l'app Nextcloud
- MCP `nextcloud-tasks` et `nextcloud-calendar` sont actifs dans Claude Code uniquement (pas Claude.ai)
