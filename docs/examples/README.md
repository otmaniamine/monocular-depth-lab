# Exemples publics

Ces trois images sont les sorties réelles d'inférences locales sur la même image publique, `assets/examples/demo01.jpg`, fournie par le [dépôt officiel Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/assets/examples/demo01.jpg). Crédit de l'image source : dépôt Depth Anything V2. Les photos personnelles ne sont pas incluses.

| Fichier | Modèle | Traitement |
| --- | --- | --- |
| `depth-anything-v2-small.png` | Depth Anything V2 Small | CPU, taille d'inférence 392 |
| `dpt-hybrid.png` | MiDaS / DPT Hybrid | CPU, prétraitement MiDaS 384 |
| `dpt-large.png` | MiDaS / DPT Large | CPU, prétraitement MiDaS 384 |

Le plus grand côté de la photo est réduit à 1280 pixels. Chaque sortie contient la photo à gauche et sa carte de profondeur à droite. La palette TURBO est appliquée après normalisation entre les percentiles 2 et 98, séparément pour chaque sortie.

Les réglages diffèrent selon le modèle : cette galerie constitue une démonstration visuelle, pas un benchmark contrôlé. Les trois cartes sont relatives, sans distances en mètres ni profondeur de référence pour calculer une erreur. Les révisions des dépôts et les empreintes des poids sont enregistrées dans `installation-stable.json` à la racine du projet.
