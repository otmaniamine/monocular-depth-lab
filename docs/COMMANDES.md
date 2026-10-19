# Commandes pour le terminal de VS Code

## Préparer le terminal

Ouvrez le dossier du projet dans VS Code, puis **Terminal > Nouveau terminal**. Choisissez **PowerShell** comme terminal. Les commandes de ce guide sont prévues pour Windows et s'exécutent depuis la racine du projet, où se trouvent `depth.py`, `reconstruct.py`, `.venv/` et `inputs/`.

L'environnement Python et les modèles doivent être installés. Les commandes utilisent directement `.venv/Scripts/python.exe` : il n'est pas nécessaire d'activer l'environnement ou de modifier la stratégie d'exécution de PowerShell.

Déposez vos médias dans `inputs/`, sans sous-dossier. Dans les exemples, remplacez `photo.jpg` ou `video.mp4` par le nom de votre fichier. Conservez les guillemets si le nom contient des espaces.

Copiez uniquement le contenu des blocs marqués `powershell`. Ne copiez pas le préfixe du terminal (`PS`, `(.venv)`, `>>`) ni la sortie du programme. Si `(.venv)` est déjà affiché dans votre terminal, les commandes ci-dessous fonctionnent aussi.

## Démarrage rapide : reconstruire vos photos en 3D

Après avoir placé vos photos d'intérieur dans `inputs/`, copiez seulement cette ligne :

```powershell
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\inputs" --model indoor --open
```

Pour des photos d'extérieur, utilisez plutôt :

```powershell
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\inputs" --model outdoor --open
```

Le programme affiche le nombre de points créés puis `Ouvrir :` avec le fichier HTML enregistré dans `results/3d/`. Cela confirme la création de la reconstruction. `--open` ouvre le premier résultat dans le navigateur.

## Comprendre les messages du terminal

- **`xFormers not available`**, éventuellement deux fois : l'optimisation xFormers est facultative et absente de cette installation. Le calcul sur CPU peut continuer ; aucun paquet supplémentaire n'est nécessaire pour les commandes présentées ici.
- **`Jeton inattendu`, `ParserError`, ou erreur sur `@echo off`** : du contenu d'un ancien lanceur Windows a été collé dans PowerShell. Ne collez pas les lignes contenant `@echo off`, `%~dp0`, `set /p` ou `if errorlevel`. Utilisez les commandes Python de ce guide.
- **Le terminal affiche `>>` et attend encore une saisie** : une commande est incomplète. Appuyez sur **Ctrl+C**, puis recopiez une commande complète depuis un bloc `powershell`.
- **Un nombre de points puis `Ouvrir :` s'affichent** : le fichier 3D a été créé. Si le navigateur ne s'ouvre pas automatiquement, ouvrez le fichier HTML indiqué ; son nom dépend de la photo.

Les anciens lanceurs ne sont plus utilisés dans la version courante. Ils peuvent toujours être présents si vous consultez une ancienne révision du projet.

## Photos : carte de profondeur

Pour une photo :

```powershell
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs\photo.jpg" --model relative
```

Pour toutes les photos et vidéos du dossier (les vidéos complètes peuvent être lentes) :

```powershell
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs" --model relative
```

Les sorties sont dans `results/relative/`.

## Vidéo : essai limité à 60 images

```powershell
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs\video.mp4" --model relative --max-frames 60
```

Retirez `--max-frames 60` pour traiter la vidéo complète.

## Comparer les trois modèles sur une photo

```powershell
foreach ($modele in @("relative", "hybrid", "large")) {
    .\.venv\Scripts\python.exe .\depth.py --input ".\inputs\photo.jpg" --model $modele
    if ($LASTEXITCODE -ne 0) { throw "Echec du modele : $modele" }
}
```

Les modèles sont exécutés successivement. Les résultats sont dans `results/relative/`, `results/hybrid/` et `results/large/`. DPT Large demande davantage de mémoire et de temps.

## Profondeur métrique estimée

Choisissez une commande selon votre scène :

```powershell
# Interieur
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs\photo.jpg" --model indoor

# Exterieur
.\.venv\Scripts\python.exe .\depth.py --input ".\inputs\photo.jpg" --model outdoor
```

Les images vont dans `results/indoor/` ou `results/outdoor/`. Les fichiers `*_meters.npy` conservent les profondeurs estimées en mètres ; ce ne sont pas des mesures certifiées.

## Photo vers reconstruction 3D

Choisissez une commande selon votre scène :

```powershell
# Photo d'interieur
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\inputs\photo.jpg" --model indoor --open

# Photo d'exterieur
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\inputs\photo.jpg" --model outdoor --open

# Toutes les photos du dossier avec le modele interieur
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\inputs" --model indoor --open
```

Les sorties vont dans `results/3d/`. `--open` ouvre le premier fichier interactif dans votre navigateur. Pour un dossier mélangeant intérieur et extérieur, traitez les photos séparément avec le modèle adapté. La reconstruction 3D accepte uniquement les photos dans cette version.

## Démonstrations 3D avec les exemples publics

Ces commandes utilisent les photos fournies par le dépôt officiel déjà téléchargé dans `source/` :

```powershell
# Escalier interieur
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\source\assets\examples\demo15.jpg" --model indoor --open

# Rue : limite des points lointains a 35 metres estimes
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\source\assets\examples\demo01.jpg" --model outdoor --max-depth 35 --open
```

Pour rouvrir l'escalier déjà généré, sans refaire le calcul :

```powershell
Start-Process ".\results\3d\demo15_indoor.html"
```

La rotation et le zoom se font dans le navigateur. Pour le format PLY, les paramètres de caméra et les limites de la reconstruction, voir le [guide 3D](RECONSTRUCTION-3D.md).

## Vérifier la géométrie

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```
