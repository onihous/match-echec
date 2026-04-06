# Guide pas à pas — Déployer le Jeu d'échecs

Ce guide est écrit pour quelqu'un qui n'est pas développeur.
Suivez chaque étape dans l'ordre, sans en sauter.

---

## ÉTAPE 1 — Installer Python sur votre PC

1. Allez sur https://www.python.org/downloads/
2. Téléchargez la dernière version de Python (3.11 ou 3.12)
3. Lancez l'installateur
4. **IMPORTANT** : cochez la case "Add Python to PATH" en bas de la fenêtre
5. Cliquez sur "Install Now"
6. Pour vérifier : ouvrez un terminal (tapez "cmd" dans la barre de recherche Windows)
   et tapez : `python --version` → ça doit afficher un numéro de version

---

## ÉTAPE 2 — Installer Git sur votre PC

Git est un outil qui permet d'envoyer votre code sur internet.

1. Allez sur https://git-scm.com/downloads
2. Téléchargez et installez Git pour Windows
3. Gardez toutes les options par défaut pendant l'installation
4. Pour vérifier : ouvrez un terminal et tapez : `git --version`

---

## ÉTAPE 3 — Créer un compte GitHub

GitHub est un site qui héberge du code. Render ira chercher votre code là-bas.

1. Allez sur https://github.com
2. Cliquez "Sign up" et créez un compte gratuit
3. Confirmez votre email

---

## ÉTAPE 4 — Tester le jeu en local (sur votre PC)

Avant de mettre le jeu en ligne, on va le tester sur votre ordinateur.

1. Ouvrez VS Code
2. Allez dans Fichier → Ouvrir le dossier → sélectionnez le dossier "jeu-echecs"
3. Ouvrez un terminal dans VS Code (menu Terminal → Nouveau terminal)
4. Tapez ces commandes une par une :

```
pip install -r requirements.txt
```

Attendez que ça s'installe (ça prend 1-2 minutes).

Puis lancez le serveur :

```
python app.py
```

5. Vous devriez voir apparaître :
   "=== Jeu d'échecs - Version 1 ==="
   "Ouvrez http://localhost:5000 dans votre navigateur"

6. Ouvrez votre navigateur web (Chrome, Firefox...) et allez à l'adresse :
   http://localhost:5000

7. Le jeu devrait s'afficher ! Entrez un prénom et testez.

8. Pour tester le multijoueur, ouvrez un 2e onglet sur la même adresse
   et entrez un autre prénom.

9. Pour arrêter le serveur : retournez dans le terminal VS Code
   et appuyez sur Ctrl+C

---

## ÉTAPE 5 — Mettre le code sur GitHub

1. Dans le terminal de VS Code (dans le dossier jeu-echecs), tapez :

```
git init
git add .
git commit -m "Version 1 du jeu d'échecs"
```

2. Allez sur GitHub dans votre navigateur :
   - Cliquez sur le "+" en haut à droite → "New repository"
   - Nom du repository : `match-echec`
   - Laissez "Public" sélectionné
   - Ne cochez rien d'autre
   - Cliquez "Create repository"

3. GitHub vous affiche des commandes. Copiez et collez dans le terminal
   les 2 lignes sous "…or push an existing repository" :

```
git remote add origin https://github.com/VOTRE_PSEUDO/match-echec.git
git branch -M main
git push -u origin main
```

(Remplacez VOTRE_PSEUDO par votre nom d'utilisateur GitHub)

4. Si on vous demande de vous connecter, entrez vos identifiants GitHub.

5. Retournez sur GitHub et rafraîchissez la page : vos fichiers doivent
   apparaître.

---

## ÉTAPE 6 — Déployer sur Render (mettre en ligne)

1. Allez sur https://render.com
2. Cliquez "Get Started for Free"
3. Inscrivez-vous avec votre compte GitHub (bouton "GitHub")
4. Une fois connecté, cliquez "New +" → "Web Service"
5. Sélectionnez votre repository "match-echec"
   (si vous ne le voyez pas, cliquez "Configure account" et autorisez Render
   à accéder à vos repositories)
6. Remplissez les champs :
   - **Name** : `match-echec` (ce sera votre URL : match-echec.onrender.com)
   - **Region** : Frankfurt (EU Central) — le plus proche de la France
   - **Branch** : main
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
   - **Instance Type** : Free
7. Cliquez "Create Web Service"
8. Render va construire et déployer votre site. Ça prend 2-5 minutes.
   Vous verrez les logs défiler.
9. Quand c'est terminé, vous verrez "Live" en vert.
10. Votre jeu est accessible à : https://match-echec.onrender.com

---

## ÉTAPE 7 — Partager le lien

Envoyez simplement l'adresse https://match-echec.onrender.com
à n'importe qui. Ils pourront jouer en ouvrant le lien dans leur navigateur.

**Note** : sur le plan gratuit de Render, le serveur s'endort après
15 minutes sans visiteur. Le premier visiteur devra attendre environ
30 secondes le temps que le serveur se réveille. Ensuite c'est instantané.

---

## En cas de problème

### "pip" n'est pas reconnu
→ Réinstallez Python en cochant bien "Add Python to PATH"

### "git" n'est pas reconnu
→ Réinstallez Git et redémarrez VS Code

### Le déploiement échoue sur Render
→ Vérifiez que vos 5 fichiers sont bien sur GitHub :
  app.py, requirements.txt, Procfile, render.yaml, templates/index.html

### La page s'affiche mais rien ne se passe
→ Ouvrez la console du navigateur (F12 → onglet Console) et
  regardez s'il y a des erreurs en rouge

---

## Pour mettre à jour le jeu plus tard

Quand vous modifierez le code :

1. Dans le terminal VS Code :
```
git add .
git commit -m "Description de la modification"
git push
```

2. Render détectera automatiquement le changement et redéploiera le site.
