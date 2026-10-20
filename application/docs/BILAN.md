# Bilan des essais réels

Essais effectués sur CPU, sans entraînement, avec les poids Depth Anything V2 Metric Small déjà installés. Les six photographies et les deux extraits vidéo proviennent de médias publics crédités dans [SOURCES.md](SOURCES.md). Le logement est réutilisé pour trois applications.

## Résultats obtenus

| Essai | Résultat calculé | Action proposée |
|---|---|---|
| Photo de rue | `ALERTE_SIMULEE`, 2 composantes géométriques | Suspendre la progression dans un simulateur et demander confirmation |
| Logement, mode robot | `VIGILANCE`, 3 composantes | Examiner les zones, prendre une autre vue |
| Logement, retouche | `EFFET_PRODUIT` | Choisir la profondeur à conserver nette et comparer les contours |
| Logement, aménagement | `GABARIT_PRODUIT` | Discuter l'emplacement puis mesurer avant achat |
| Stockage de cartons | `ALERTE_SIMULEE`, 2 composantes | Inspecter le passage et déplacer uniquement les objets réellement gênants |
| Allée d'entrepôt | `VIGILANCE` | Examiner les surfaces détectées près des rayonnages |
| Vidéo routière frontale | 12 vues : 9 `VIGILANCE`, 3 alertes individuelles | Les 3 alertes restent `ALERTE_A_CONFIRMER` temporellement |
| Vidéo latérale explicitement déclarée | 6 vues : 6 `ABSTENTION` | Repositionner la caméra pour obtenir une vue frontale |

Les comptes sont des sorties de ce traitement, **pas des scores de précision** ni un comptage des objets présents. Les données détaillées sont dans [bilan.json](bilan.json) et les rapports de chaque application.

## Observations et limites constatées

- La rue photographiée produit deux grandes régions sur des véhicules latéraux. L'alerte ne démontre pas qu'ils coupent la trajectoire centrale et ne garantit pas la détection du piéton visible plus loin.
- Dans le logement, le masque regroupe des meubles et des portions de paroi. Le programme ne sait pas nommer un fauteuil ou distinguer sa fonction. La caméra est à hauteur humaine, pas au niveau d'un aspirateur.
- Dans l'entrepôt, des piles de cartons latérales déclenchent l'alerte. Leur présence dans une grande zone de surveillance ne prouve pas une obstruction du passage : le responsable doit confirmer la gêne.
- Sur la première vue vidéo, une partie du bord du trottoir est marquée, alors que les véhicules de gauche ne sont pas tous retenus. Cela montre des omissions et des sélections à revoir avant toute utilisation de navigation.
- Aucune suite de trois alertes consécutives n'apparaît dans les douze vues routières. Le filtre temporel ne confirme donc aucune alerte persistante sur cet extrait ; cela ne signifie pas que la route est sûre.
- Le refus de la vidéo latérale résulte de l'option `--camera-lateral`, donnée par l'utilisateur. L'orientation n'est pas reconnue automatiquement.
- Le flou conserve la zone du fauteuil à la profondeur choisie et atténue les autres profondeurs ; les contours restent approximatifs.
- Le volume de meuble est projeté avec occlusion : certains pixels virtuels sont cachés par les surfaces estimées de la scène. Les dimensions restent supposées et l'orientation suit la caméra.

## Prochaines étapes utiles

1. **Projet démontrable dès maintenant :** photo → profondeur → visualisation → résultat d'application → rapport d'action, avec commandes PowerShell et galerie hors ligne.
2. **Navigation :** filmer avec une caméra fixe à la bonne hauteur, calibrer, annoter des scènes contenant des obstacles et des passages sans obstacle. Évaluer les objets manqués et les fausses alertes ; intégrer ensuite une simulation de déplacement et une perception complémentaire si nécessaire.
3. **Entreprise :** charger un modèle de meuble réel, orienter le volume par rapport au sol et calibrer l'échelle avec une dimension mesurée. Comparer une implantation proposée à une mesure sur place avant de présenter un bénéfice commercial.
4. **Industrie :** définir le passage dans les coordonnées du sol avec une caméra fixe, mesurer sa largeur réellement disponible, puis comparer les alertes à des annotations humaines. Le prototype actuel ne calcule pas cette largeur.

Les tests numériques contrôlent des scènes synthétiques connues et des protections de publication des exemples. Les essais réels valident l'exécution et illustrent les erreurs observées ; ils ne constituent pas une validation de sécurité ou une évaluation sur un dataset annoté.

## Reproduire la sélection publique

Lancer les cinq démonstrations, puis les trois commandes supplémentaires documentées pour la vidéo frontale, la vidéo latérale et l'allée. Ensuite :

```powershell
.\.venv\Scripts\python.exe -m application.tools.build_examples
```

Cette commande vérifie les empreintes du manifeste et les noms de sources publiques attendus. Elle copie seulement les vues référencées dans le rapport courant ; les résultats provenant d'une entrée utilisateur sont refusés. Elle ne pousse rien vers GitHub.
