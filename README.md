# QPUC GameMaster (Python)

Objectif : piloter **1 Whiteboard** (affichage côté GameMaster) + **2 Controllers** (interaction joueurs) pour une manche **"4 à la suite"** en **QCM 4 choix**.

- Timer : **45s par joueur**
- Score : **+1 si bon**, **0 sinon**
- Victoire : premier à **4 points**

## Dépendances

- Python 3
- `ingescape>=4`
- `requests`

```bash
pip install -r requirements.txt
```

## Lancer

### 1) Lancer les Whiteboards

Lancer le Whiteboard sur le **PC GameMaster** (le joueur 2 regarde cet écran).

### 2) Lancer le GameMaster (sur le PC J1)

Lancer le script correspond au nombre de controller que vous voulez afficher sur le PC GameMaster.

Par défaut, le GameMaster lance automatiquement 2 controllers **sur le même PC** (2 fenêtres). Pour désactiver : `--no-controllers`.

Si tu veux que **J2 n'ait que son Controller** sur son PC, lancer le script `Controller_J2.bat` sur le PC de J2.

## Câblage Ingescape (important)

Le setup est : **Whiteboard = affichage uniquement** et **Controllers = interaction**.

### 1) Réponses (A/B/C/D)

- Lien 1 : `QPUC_Controller_P1 / answer` -> `QPUC_GameMaster / click_p1`
- Lien 2 : `QPUC_Controller_P2 / answer` -> `QPUC_GameMaster / click_p2`

Pour démarrer avec 2 boutons "Prêt" (un par joueur) :

- Lien 3 : `QPUC_Controller_P1 / ready` -> `QPUC_GameMaster / ready_p1`
- Lien 4 : `QPUC_Controller_P2 / ready` -> `QPUC_GameMaster / ready_p2`

Quand `ready_p1` et `ready_p2` sont à True, la partie démarre automatiquement.

Pour que le bouton "Prêt" se désactive automatiquement quand la partie démarre (et se réarme après reset), relie l’état du GameMaster :

- Lien 5 : `QPUC_GameMaster / state` -> `QPUC_Controller_P1 / gm_state`
- Lien 6 : `QPUC_GameMaster / state` -> `QPUC_Controller_P2 / gm_state`

Pour demander un reset à 2 joueurs (bouton Reset côté controllers) :

- Lien 7 : `QPUC_Controller_P1 / reset` -> `QPUC_GameMaster / reset_p1`
- Lien 8 : `QPUC_Controller_P2 / reset` -> `QPUC_GameMaster / reset_p2`

Lancement (exemple):

```bash
python ..\qpuc_controller_py\main.py --player 1 --port 4646 --device "NOM_DE_LA_CARTE_RESEAU" --verbose
python ..\qpuc_controller_py\main.py --player 2 --port 4646 --device "NOM_DE_LA_CARTE_RESEAU" --verbose
```

Penser à modifier le fichier .bat pour changer le port et le device

### 2) Whiteboard responsive (recommandé)

Le Whiteboard expose des outputs de taille, que le GameMaster peut utiliser pour adapter la mise en page.

- Lien : `Whiteboard / windowWidth` -> `QPUC_GameMaster / wb_p1_windowWidth`
- Lien : `Whiteboard / windowHeight` -> `QPUC_GameMaster / wb_p1_windowHeight`
- Lien : `Whiteboard / whiteboardWidth` -> `QPUC_GameMaster / wb_p1_whiteboardWidth`
- Lien : `Whiteboard / whiteboardHeight` -> `QPUC_GameMaster / wb_p1_whiteboardHeight`

## Commandes

- Pour démarrer une partie : Appuyer sur Prêt sur les 2 controllers.
- Pour revenir à l’état initial : Appuyer sur Reset sur les 2 controllers.

## Fichiers

- `main.py` : bootstrap Ingescape + IO + boucle/timer
- `gamemaster.py` : logique de jeu + rendu Whiteboard
- `trivia.py` : récupération de questions (OpenTDB)
