# Médias d'entrée

Copiez vos photos et vidéos directement dans ce dossier, sans sous-dossier.
Depuis la racine du projet, dans le terminal PowerShell de VS Code, exécutez :

```powershell
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs" --model relative
```

Les résultats seront enregistrés dans `results/relative/`.

Pour la reconstruction 3D, les vidéos et la comparaison des modèles, voir le [guide des commandes](../docs/COMMANDES.md).

Les médias de ce dossier restent locaux et sont exclus de Git. Seul ce fichier de documentation est publié.
