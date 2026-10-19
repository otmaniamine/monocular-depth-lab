# Commandes pour le terminal de VS Code

## Préparer le terminal

Ouvrez le dossier du projet dans VS Code, puis **Terminal > Nouveau terminal**. Choisissez **PowerShell** comme terminal. Les commandes de ce guide sont prévues pour Windows et s'exécutent depuis la racine du projet, où se trouvent `depth.py`, `reconstruct.py`, `.venv/` et `inputs/`.

L'environnement Python et les modèles doivent être installés. Les commandes utilisent directement `.venv/Scripts/python.exe` : il n'est pas nécessaire d'activer l'environnement ou de modifier la stratégie d'exécution de PowerShell.

Déposez vos médias dans `inputs/`, sans sous-dossier. Dans les exemples, remplacez `photo.jpg` ou `video.mp4` par le nom de votre fichier. Conservez les guillemets si le nom contient des espaces.

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
