# Claude Usage Meter

Widget desktop Ubuntu KDE Plasma (tray + petite fenetre always-on-top) pour surveiller la `Session actuelle` de `https://claude.ai/settings/usage`.

## Fonctionnalites
- Refresh toutes les 2 minutes (configurable)
- Barre d'usage + pourcentage + texte de reinitialisation
- Alerte popup + son au passage >= 80% (une fois par session)
- Icône tray: afficher/masquer, refresh force, quitter
- Installation autostart Ubuntu

## Installation
Si ton projet est sur `/media/...`, cree le venv dans `$HOME` (sinon `Permission denied` sur les binaires).

```bash
python3 -m venv ~/.venvs/claude-usage-meter
source ~/.venvs/claude-usage-meter/bin/activate
python -m pip install -e .
python -m playwright install chromium
```

## Lancement
```bash
claude-usage-meter
```

## Initialiser la session Claude (premiere fois)
```bash
claude-usage-meter-login
```
Cette commande ouvre Chromium avec le profil dedie de l'app. Connecte-toi a Claude, puis ferme la fenetre.

## Autostart Ubuntu
```bash
claude-usage-meter-install-autostart
```

## Configuration
Le fichier est cree automatiquement dans:
`~/.config/claude-usage-meter/config.toml`

Valeurs par defaut:
- `refresh_seconds = 120`
- `threshold_percent = 80`
- `always_on_top = true`
- `play_sound = true`
- `chromium_executable = "/snap/bin/chromium"`
- `profile_dir = "~/claude-usage-meter-profile"`
- `headless = false`

## Notes
- Cette app utilise un profil Chromium dedie pour eviter les verrous `SingletonLock`.
- Le profil est volontairement dans `~/...` (non cache) pour compatibilite Snap Chromium.
- Si tu changes `profile_dir` vers le profil principal Chromium, il faut fermer Chromium avant lancement.
- Chromium est lance avec une classe de fenetre dediee: `claude-usage-meter-browser` (utile pour les regles KDE ciblees).
