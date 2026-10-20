# Organisation du projet

```text
monocular-depth-lab/
├── README.md                 Guide de démarrage
├── depth.py                  Commande de profondeur
├── reconstruct.py            Commande de reconstruction 3D
├── pointcloud.py              Géométrie et exports 3D
├── viewer3d.html              Modèle de visionneuse
├── requirements-lock.txt      Versions des dépendances
├── installation-stable.json   Références de l'installation validée
├── VERSION-STABLE.md          Guide de restauration Git
├── docs/                      Guides et illustrations du projet
├── application/
│   ├── README.md              Commandes des applications
│   ├── index.html             Galerie locale
│   ├── run.py                 Commande commune des applications
│   ├── geometry.py            Traitements géométriques et photographiques
│   ├── tools/                 Préparation des médias et de la galerie
│   ├── docs/                  Bilan, sources et synthèse JSON
│   ├── assets/                Médias publics crédités et manifeste
│   └── 01_... à 05_.../       Applications, guides et exemples publics
├── tests/                     Tests numériques et vérifications navigateur
├── inputs/                    Vos photos et vidéos (local)
├── results/                   Résultats de travail (local)
├── source/ et midas/          Dépôts et poids téléchargés (local)
├── .venv/                    Environnement Python (local)
└── sauvegardes/               Sauvegardes privées (local)
```

Les commandes principales restent à la racine pour conserver leur utilisation depuis le terminal de VS Code. Les outils de préparation s'appellent désormais avec `python -m application.tools.prepare_assets` et `python -m application.tools.build_examples` ; utiliser le Python de `.venv` comme indiqué dans les guides.

Seuls les exemples publics crédités de `application/` et `docs/` sont versionnés. Les médias personnels, résultats de travail, poids et environnements restent exclus de Git. `inputs/README.md` est conservé comme guide.
