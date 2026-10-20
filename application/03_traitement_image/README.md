# Traitement d'image : flou guidé par la profondeur

**Problème :** mettre en valeur un sujet sans dessiner manuellement un masque complet. **Usage :** retouche de photos produit, contenu publicitaire ou effet photographique.

![Photo, profondeur et retouche calculée](exemples/vue_001_comparaison.jpg)

L'utilisateur choisit un point de mise au point. Le programme calcule la profondeur médiane d'un petit voisinage et applique un flou progressif lorsque la profondeur s'éloigne de cette valeur. Il combine plusieurs versions de l'image floutées à des intensités différentes. Le résultat ne dépend pas d'une segmentation ou d'un entraînement supplémentaire.

```powershell
.\.venv\Scripts\python.exe -m application.run --demo photo
.\.venv\Scripts\python.exe -m application.run --app photo --input ".\inputs\produit.jpg" --focus 0.50 0.55
```

Le point `(0.35, 0.66)` de la démonstration correspond au fauteuil. Modifier `--focus X Y` pour changer le sujet. La croix est présente dans l'image de comparaison ; le fichier `vue_001_resultat.jpg` conserve la retouche sans croix. Le masque exporté représente l'intensité du flou, pas une classe d'objet.

Action : comparer avec l'original, déplacer le point de mise au point, puis conserver la retouche si les contours conviennent. Le mélange est approximatif et peut produire des halos autour des objets fins ; il ne reproduit pas exactement l'optique d'un objectif.

[Rapport calculé](exemples/RAPPORT.md) · [Paramètres](exemples/rapport.json) · [Sources](../SOURCES.md)
