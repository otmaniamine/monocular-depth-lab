# Version stable v1.0.0

Version de référence : exécution locale des modèles préentraînés sur les photos et vidéos, sans entraînement. Les essais initiaux ont porté sur les cinq jeux de poids pour les photos et trois images vidéo avec Depth Anything V2 Small.

## Organisation Git

- `main` présente la version courante publiée du projet.
- Le tag `v1.0.0` désigne exactement cette sauvegarde.
- La branche `developpement` accueille les prochaines améliorations.

Un fork sert à créer une copie d'un dépôt, généralement sur une plateforme comme GitHub. Pour travailler sur une nouvelle étape dans ce projet local, une branche suffit.

## Retrouver cette version

Ouvrez PowerShell à la racine de votre copie du projet :

```powershell
git status
```

S'il reste des modifications non enregistrées, sauvegardez-les avant de changer de branche :

```powershell
git stash push -u -m "Travail avant retour a v1.0.0"
```

Pour consulter et tester exactement la version de référence, sans commencer de nouvelles modifications :

```powershell
git switch --detach v1.0.0
```

Pour développer à partir de cette version de référence, créez plutôt une nouvelle branche depuis le tag :

```powershell
git switch -c reprise-v1.0.0 v1.0.0
```

Pour reprendre les améliorations :

```powershell
git switch developpement
```

Si vous aviez utilisé `git stash`, retrouvez les sauvegardes avec `git stash list` et appliquez celle voulue avec `git stash apply`. Si Git signale un conflit, réglez-le avant de continuer.

## Contenu de la sauvegarde

Git conserve le programme local, la documentation, `requirements-lock.txt` et `installation-stable.json` (références des deux dépôts officiels et empreintes des cinq fichiers de poids). Les dépôts dans `source` et `midas`, l'environnement `.venv`, les poids, les photos personnelles et les résultats restent sur le disque et ne changent pas quand vous changez de branche. Un changement futur de dépendances devra donc gérer son propre environnement si nécessaire.

Les branches `main` et `developpement` et le tag `v1.0.0` sont publiés sur GitHub. Les fichiers lourds et médias exclus de Git nécessitent une sauvegarde distincte. Les archives Git locales (`*.bundle`) restent privées et ne doivent pas être publiées.

Pour reconstituer les fichiers lourds sur une autre machine, utilisez les liens et révisions de `installation-stable.json`. Recréez ensuite un environnement Python 3.12 et installez les versions enregistrées :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

Cette reconstruction exige une connexion Internet et la disponibilité des fichiers d'origine.
