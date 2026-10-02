# Guide opérations Zaeldryk

> Fiche de référence locale — générée le **26 août 2026**

---

## 1. Accès VPS

| Élément | Valeur |
|---------|--------|
| **Hôte** | `ubuntu@57.128.177.132` (OVH) |
| **Clé SSH (Windows)** | `C:\Users\nacim\Documents\projet\vps to\ssh-key-ovh-2026-08-28` |
| **Clé SSH secondaire** | `C:\Users\nacim\Documents\projet\vps to\ssh-key-2026-08-22.key` |
| **Racine projet VPS** | `/home/ubuntu/zaeldryk` |
| **Backups VPS** | `/home/ubuntu/backups/` |
| **Ancien VPS** | `ubuntu@88.96.45.10` (services arrêtés le 28 août 2026) |

### Connexion SSH (PowerShell)

```powershell
ssh -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-ovh-2026-08-28" -o StrictHostKeyChecking=no ubuntu@57.128.177.132
```

### Copier un fichier local → VPS

```powershell
scp -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-ovh-2026-08-28" -o StrictHostKeyChecking=no "CHEMIN\LOCAL\fichier.py" ubuntu@57.128.177.132:/home/ubuntu/zaeldryk/discord/
```

### Copier VPS → local

```powershell
scp -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-ovh-2026-08-28" -o StrictHostKeyChecking=no ubuntu@57.128.177.132:/home/ubuntu/zaeldryk/config/discord.env "C:\Users\nacim\Documents\projet\backup-local\"
```

---

## 2. Projet local (Windows)

| Élément | Chemin |
|---------|--------|
| **Workspace** | `C:\Users\nacim\Documents\projet` |
| **Code Zaeldryk** | `C:\Users\nacim\Documents\projet\Apps\TwitchXLive\zaeldryk\` |
| **Ce guide** | `C:\Users\nacim\Documents\projet\GUIDE-ZAELDRYK.md` |

Structure principale :

```
zaeldryk/
├── config/          # Fichiers .env (secrets — ne pas committer)
├── discord/         # Bots Discord (news, jeux gratuits, engagement, captcha…)
├── twitch/          # Live orchestrator, offline stream, cron helpers
├── x/               # Posts X (désactivé par défaut : X_ENABLED=0)
├── systemd/         # Unités à installer sur le VPS
├── tools/           # Scripts admin / deploy / debug
├── lib/common.sh    # Helpers Twitch partagés
├── state/           # État runtime (mode live, locks, historiques)
└── logs/            # Journaux applicatifs
```

---

## 3. Twitch

| Élément | Valeur |
|---------|--------|
| **Chaîne** | https://twitch.tv/zaeldryk |
| **Login** | `zaeldryk` |
| **Broadcaster ID** | `426411773` |
| **Token OAuth** | `/home/ubuntu/twitch_token.txt` |
| **Config** | `/home/ubuntu/zaeldryk/config/twitch.env` |
| **Horaire streams visé** | ~22h–23h30 (Paris) |

### Comportement live (automatique)

Le service **`zaeldryk-live.service`** exécute `twitch/live-orchestrator.sh` :

- Détecte live / offline / fin de live (poll ~10 s)
- **Début de live** : annonce Discord gérée par **Streamcord** (pas de doublon chat Twitch)
- **Pendant le live** : rappel Discord chat toutes les **15 min**
- **Fin de live** : message chat « Merci d'avoir regardé ! »
- **Offline** : démarre `twitch-offline.service` (stream placeholder ffmpeg)
- **X/Twitter** : désactivé par défaut (`X_ENABLED=0` dans twitch.env)

---

## 4. Discord

| Élément | Valeur |
|---------|--------|
| **Serveur (Guild ID)** | `867426693286461490` |
| **Config bot** | `/home/ubuntu/zaeldryk/config/discord.env` |

### Salons importants

| Salon | ID | Usage |
|-------|-----|-------|
| **#📢-annonces** | `1541249724902809692` | Annonces manuelles (scripts tools/) |
| **#🎮-jeux** | `1541249730993201354` | Prompt engagement quotidien 18h Paris |
| **#🔔-actualités** | `1541251086005047390` | Bot actualités gaming/tech |
| **#🖥️-vps** | `1541249740145172581` | Alertes watchdog services |
| **Présentations** | `1541274991197159444` | Accueil nouveaux membres (bot Discord) |

### Bots / rôles

| Élément | ID / note |
|---------|-----------|
| **BOT_modération** (rôle) | `1541249416374259863` |
| **Avatar loup** | Défini sur le bot (pas icône rôle — boost lvl 2 requis) |
| **Jeux gratuits** | Epic, PSN, Xbox Game Pass, GOG, Steam |
| **Disboard bump** | **Supprimé** — ne pas réactiver |

---

## 5. Services systemd (VPS)

### Services permanents (toujours actifs)

| Service | Rôle |
|---------|------|
| `zaeldryk-live.service` | Orchestrateur live Twitch |
| `zaeldryk-discord.service` | Bot Discord principal (captcha, accueil…) |
| `moderation-bot.service` | Bot modération |
| `offline-chatbot.service` | Chatbot quand offline |
| `twitch-offline.service` | Stream ffmpeg placeholder (selon mode) |

### Timers (tâches planifiées)

| Timer | Fréquence | Action |
|-------|-----------|--------|
| `zaeldryk-news.timer` | Toutes les **30 min** | Actualités → #🔔-actualités |
| `zaeldryk-freegames.timer` | **09:00** et **17:00** UTC | Jeux gratuits |
| `zaeldryk-games-prompt.timer` | **16:00 UTC** (= 18h Paris été) | Question #🎮-jeux |
| `zaeldryk-discord-dump.timer` | Toutes les **2 h** | Dump structure serveur |
| `zaeldryk-watchdog.timer` | Toutes les **1 min** | Surveillance services → #🖥️-vps |

### Commandes systemd essentielles

```bash
# État global
systemctl list-units 'zaeldryk-*' 'twitch-*' 'moderation-*' 'offline-*' --no-pager

# Prochaines exécutions timers
systemctl list-timers 'zaeldryk-*' --no-pager

# Redémarrer l'orchestrateur live
sudo systemctl restart zaeldryk-live.service

# Logs en direct (dernières lignes)
journalctl -u zaeldryk-live.service -f --no-pager
journalctl -u zaeldryk-discord.service -f --no-pager
```

---

## 6. Cron (ubuntu)

Fichier de référence : `/home/ubuntu/zaeldryk/crontab.zaeldryk`

| Fréquence | Script | Rôle |
|-----------|--------|------|
| Toutes les 3 h | `twitch/refresh-token.sh` | Renouvelle token Twitch |
| Toutes les 15 min | `twitch/delete-offline-vods.sh` | Nettoie VODs offline |
| Toutes les 15 min | `twitch/clear-chat-offline.sh` | Vide chat offline |
| Toutes les 2 h | `twitch/reset-offline.sh` | Redémarre stream offline |

Voir le crontab actif :

```bash
crontab -l
```

---

## 7. Fichiers de configuration (.env)

> **Ne jamais committer les vrais tokens.** Garder des copies locales chiffrées ou sur clé USB.

| Fichier | Contenu |
|---------|---------|
| `config/discord.env` | `DISCORD_BOT_TOKEN`, `DISCORD_ALERT_CHANNEL_ID` |
| `config/twitch.env` | Client ID, broadcaster, chemins token, `X_ENABLED` |
| `config/news.env` | `NEWS_CHANNEL_ID`, `NEWS_MIN_DATE`, limites |
| `config/freegames.env` | `FREEGAMES_CHANNEL_ID` |
| `config/games-prompt.env` | `GAMES_CHANNEL_ID` |
| `/home/ubuntu/twitch_token.txt` | Token OAuth Twitch (hors repo) |
| `/home/ubuntu/x_config.env` | Config X (si réactivé un jour) |

Exemples sans secrets : `config/*.env.example`

---

## 8. Logs utiles

```bash
# Sur le VPS
tail -f /home/ubuntu/zaeldryk/logs/live-orchestrator.log
tail -f /home/ubuntu/zaeldryk/logs/service-watchdog.log
tail -f /home/ubuntu/zaeldryk/logs/freegames-bot.log
tail -f /home/ubuntu/zaeldryk/logs/news-bot.log

# État live actuel
cat /home/ubuntu/zaeldryk/state/mode.txt
```

---

## 9. Règle d'or — backup avant modification VPS

**Toujours** créer un backup horodaté avant d'éditer scripts, cron ou systemd :

```bash
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p /home/ubuntu/backups/${STAMP}_nom-tache/
cp -a /home/ubuntu/zaeldryk/FICHIER /home/ubuntu/backups/${STAMP}_nom-tache/
crontab -l > /home/ubuntu/backups/${STAMP}_nom-tache/crontab.txt
```

### Archive complète (migration VPS)

```bash
bash /home/ubuntu/zaeldryk/tools/make-vps-migration-pack.sh
# → /home/ubuntu/backups/YYYY-MM-DD_HHMM_zaeldryk-vps-migration.tar.gz
```

Archive existante (26 août 2026) :
- `/home/ubuntu/backups/2026-08-26_0813_zaeldryk-vps-migration.tar.gz`
- SHA256 : `acb91f32…` (vérifier avec `sha256sum` sur le VPS)

---

## 10. Déployer une modification

### Workflow typique

1. Éditer en local dans `Apps\TwitchXLive\zaeldryk\`
2. **Backup sur le VPS** (section 9)
3. `scp` du fichier modifié
4. Redémarrer le service concerné

### Exemples

```bash
# News bot
bash /home/ubuntu/zaeldryk/tools/deploy-news-bot.sh

# Jeux gratuits
bash /home/ubuntu/zaeldryk/tools/deploy-freegames-bot.sh

# Prompt #🎮-jeux
bash /home/ubuntu/zaeldryk/tools/deploy-games-prompt.sh

# Watchdog
bash /home/ubuntu/zaeldryk/tools/install-watchdog-on-vps.sh
```

Après modification d'une unité systemd :

```bash
sudo cp /home/ubuntu/zaeldryk/systemd/NOM.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now NOM.service   # ou .timer
sudo systemctl restart NOM.service
```

---

## 11. Scripts admin utiles

| Script | Usage |
|--------|-------|
| `tools/list-channels.py` | Lister salons Discord |
| `tools/check-role-hierarchy.py` | Hiérarchie rôles / premium tier |
| `tools/set-bot-avatar.py` | Changer avatar bot modération |
| `tools/check-follower-count.sh` | Followers Twitch (API Helix) |
| `tools/post-stream-resume-announce.py` | Annonce reprise streams |
| `tools/post-security-announce.py` | Annonce sécurité Discord |
| `tools/purge-news-channel.py` | Vider #🔔-actualités |
| `tools/test-free-sources.py` | Tester sources jeux gratuits |
| `tools/test-rss.py` | Tester flux actualités |
| `discord/server-dump.py` | Dump JSON structure serveur |

Lancer un script Python sur le VPS :

```bash
cd /home/ubuntu/zaeldryk
python3 tools/list-channels.py
```

---

## 12. Dépannage rapide

### Un bot ne répond plus

```bash
systemctl status moderation-bot.service zaeldryk-discord.service --no-pager
sudo systemctl restart moderation-bot.service zaeldryk-discord.service
```

### Actualités ne partent plus

```bash
systemctl status zaeldryk-news.timer --no-pager
python3 /home/ubuntu/zaeldryk/tools/test-rss.py
tail -50 /home/ubuntu/zaeldryk/logs/news-bot.log
# Vérifier NEWS_MIN_DATE dans config/news.env
```

### Live non détecté

```bash
systemctl status zaeldryk-live.service --no-pager
tail -30 /home/ubuntu/zaeldryk/logs/live-orchestrator.log
cat /home/ubuntu/twitch_token.txt | wc -c   # token non vide ?
bash /home/ubuntu/zaeldryk/twitch/refresh-token.sh
```

### Alertes VPS spam Discord

```bash
tail -30 /home/ubuntu/zaeldryk/logs/service-watchdog.log
# Silence temporaire offline (180 s) — utilisé par reset-offline cron
cat /home/ubuntu/zaeldryk/state/watchdog-silence-offline.txt
```

### Token Discord expiré / 401

Regénérer sur https://discord.com/developers/applications → mettre à jour `config/discord.env` → redémarrer les services bot.

---

## 13. Fichiers sensibles à sauvegarder (hors git)

- [ ] `vps to\ssh-key-2026-08-22.key`
- [ ] Copie locale de `config/*.env` (depuis VPS)
- [ ] `/home/ubuntu/twitch_token.txt`
- [ ] Ce guide + dossier `Apps\TwitchXLive\zaeldryk\`
- [ ] Archive migration VPS (sections 9 et 15)

---

## 14. Liens utiles

| Ressource | URL |
|-----------|-----|
| Twitch dashboard | https://dashboard.twitch.tv |
| Discord Developer Portal | https://discord.com/developers/applications |

---

## 15. Migration vers un autre VPS

> Discord et Twitch **ne dépendent pas de l’IP** du serveur.  
> **Règle :** ne jamais laisser l’ancien et le nouveau VPS actifs en même temps (même token bot = conflit).

### Schéma

```
Ancien VPS → archive .tar.gz → PC (backup) → nouveau VPS → services relancés
```

### A. Créer l’archive (ancien VPS)

Connexion :

```powershell
ssh -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-2026-08-22.key" -o StrictHostKeyChecking=no ubuntu@88.96.45.10
```

Générer le pack (inclut code, `.env`, systemd, crontab, token Twitch, `thanks.mp4`, `RESTORE.md`) :

```bash
bash /home/ubuntu/zaeldryk/tools/make-vps-migration-pack.sh
```

Résultat :

```text
/home/ubuntu/backups/YYYY-MM-DD_HHMM_zaeldryk-vps-migration.tar.gz
/home/ubuntu/backups/YYYY-MM-DD_HHMM_vps-migration-pack/SHA256.txt
```

Vérifier l’intégrité :

```bash
sha256sum /home/ubuntu/backups/*_zaeldryk-vps-migration.tar.gz
cat /home/ubuntu/backups/*_vps-migration-pack/SHA256.txt
```

### B. Télécharger en local (Windows)

```powershell
mkdir "C:\Users\nacim\Documents\projet\backup-local" -Force
scp -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-2026-08-22.key" -o StrictHostKeyChecking=no "ubuntu@88.96.45.10:/home/ubuntu/backups/*_zaeldryk-vps-migration.tar.gz" "C:\Users\nacim\Documents\projet\backup-local\"
```

Conserver aussi une copie sur clé USB ou cloud.

### C. Préparer le nouveau VPS

- **OS :** Ubuntu 22.04 ou 24.04
- **User :** `ubuntu` avec sudo
- **Clé SSH :** installer ta clé publique sur le nouveau serveur
- **Specs mini :** 2 Go RAM, 20 Go disque (Contabo, Hetzner, etc.)

Paquets sur le **nouveau** VPS :

```bash
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg curl jq rsync util-linux
pip3 install aiohttp discord.py
```

(`flock` est dans `util-linux`.)

### D. Envoyer l’archive sur le nouveau VPS

Remplacer `NOUVELLE_IP` et le chemin de clé si différent :

```powershell
scp -i "C:\Users\nacim\Documents\projet\vps to\ssh-key-2026-08-22.key" -o StrictHostKeyChecking=no "C:\Users\nacim\Documents\projet\backup-local\*_zaeldryk-vps-migration.tar.gz" ubuntu@NOUVELLE_IP:/home/ubuntu/
```

### E. Restaurer sur le nouveau VPS

```bash
cd /home/ubuntu
tar -xzf *_zaeldryk-vps-migration.tar.gz
cd *_vps-migration-pack/zaeldryk-migration

# Code + configs
sudo rsync -a zaeldryk/ /home/ubuntu/zaeldryk/
sudo chown -R ubuntu:ubuntu /home/ubuntu/zaeldryk

# Vidéo stream offline
cp extras/thanks.mp4 /home/ubuntu/thanks.mp4

# Token Twitch (si présent dans l’archive)
if [[ -f extras/tokens/PATH.txt ]]; then
  TOKEN_PATH=$(grep TWITCH_TOKEN_FILE extras/tokens/PATH.txt | cut -d= -f2)
  mkdir -p "$(dirname "$TOKEN_PATH")"
  cp extras/tokens/* "$(dirname "$TOKEN_PATH")/" 2>/dev/null || true
fi

# Systemd
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Sudoers (orchestrateur live → start/stop offline stream)
sudo cp /home/ubuntu/zaeldryk/systemd/zaeldryk-offline.sudoers /etc/sudoers.d/zaeldryk-offline
sudo chmod 440 /etc/sudoers.d/zaeldryk-offline

# Activer tous les services et timers
sudo systemctl enable --now zaeldryk-live.service zaeldryk-discord.service \
  moderation-bot.service offline-chatbot.service twitch-offline.service \
  zaeldryk-news.timer zaeldryk-freegames.timer zaeldryk-games-prompt.timer \
  zaeldryk-discord-dump.timer zaeldryk-watchdog.timer

# Cron
crontab cron/ubuntu.crontab
```

Le détail est aussi dans `RESTORE.md` **à l’intérieur de l’archive**.

### F. Vérifications post-migration

```bash
systemctl status zaeldryk-live zaeldryk-discord moderation-bot offline-chatbot --no-pager
systemctl list-timers 'zaeldryk-*' --no-pager
crontab -l

bash /home/ubuntu/zaeldryk/twitch/refresh-token.sh
bash /home/ubuntu/zaeldryk/tools/check-follower-count.sh

tail -30 /home/ubuntu/zaeldryk/logs/live-orchestrator.log
python3 /home/ubuntu/zaeldryk/tools/test-rss.py
```

Côté Discord : bot en ligne, message test dans `#🖥️-vps` (watchdog), actu dans `#🔔-actualités`.

### G. Basculer (couper l’ancien VPS)

**Sur l’ancien VPS** — arrêter tout avant de laisser le nouveau tourner seul :

```bash
sudo systemctl stop zaeldryk-live zaeldryk-discord moderation-bot offline-chatbot twitch-offline
sudo systemctl stop zaeldryk-news.timer zaeldryk-freegames.timer zaeldryk-games-prompt.timer
sudo systemctl stop zaeldryk-discord-dump.timer zaeldryk-watchdog.timer
sudo systemctl disable zaeldryk-live zaeldryk-discord moderation-bot offline-chatbot twitch-offline
```

Puis résilier l’ancien serveur quand le nouveau est validé.

### H. Fichiers critiques (inclus dans l’archive)

| Fichier | Rôle |
|---------|------|
| `config/discord.env` | Token bot Discord |
| `config/twitch.env` | Client ID, refresh token Twitch |
| `config/stream.env` | Clé RTMP stream offline |
| `/home/ubuntu/twitch_token.txt` | Token OAuth actif |
| `config/news.env` | Salon actualités + filtres |
| `config/freegames.env` | Salon jeux gratuits |
| `config/games-prompt.env` | Salon #🎮-jeux |

### I. Mettre à jour ce guide après migration

Modifier dans ce fichier :

- Section **1** : nouvelle IP / clé SSH
- Ligne de pied de page : nouvelle IP
- Section **13** : nouvelle archive de backup

---

*Dernière mise à jour : 28 août 2026 — stack migrée sur OVH `57.128.177.132`*
