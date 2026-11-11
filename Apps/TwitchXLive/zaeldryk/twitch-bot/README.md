# Bot Twitch Zaeldryk

Bot de chat pour [twitch.tv/zaeldryk](https://twitch.tv/zaeldryk). Il remplace WizeBot : commandes, timers, modération, événements et relais TikTok. Il n’est pas encore lancé sur le VPS. Il ne faut pas le démarrer tant que le compte bot Twitch n’existe pas et que le fichier `.env` n’est pas rempli.

## Ce qu’il fait

- Il se connecte au chat avec un compte bot dédié. Le jeton OAuth est renouvelé tout seul.
- Les commandes `!discord`, `!tiktok`, `!planning`, `!commandes` sont dans `commands.example.json`. Les mods peuvent en ajouter avec `!addcmd`, `!editcmd` et `!delcmd`.
- Chaque commande a un cooldown et un niveau : `everyone`, `sub`, `vip`, `mod` ou `broadcaster`. Un mod peut utiliser les commandes d’un palier plus bas.
- Les messages automatiques partent seulement si le chat a envoyé assez de messages depuis le dernier envoi. Le réglage est dans `timers.example.json`.
- La modération retire les liens (sauf `!permit pseudo`, un lien pendant 60 secondes), le spam, les répétitions et l’excès de majuscules. Les timeouts de ces règles montent : 60 s, 5 min, 10 min, 30 min, 1 h. Les VIP, mods et le broadcaster ne sont pas touchés par ces règles-là.
- Les propos haineux (liste dans `moderation.example.json`, extensible avec `!addhate` et `!delhate`) suppriment le message et bannissent tout de suite. Seuls le broadcaster et les mods y échappent : un VIP n’y échappe pas.
- Le spam de vente de viewers, followers ou primes, et les raccourcis suspects, suppriment le message et bannissent.
- La pub vers une autre chaîne ou un autre Discord supprime le message et prévient en public. Les liens de Zaeldryk (Twitch, TikTok, YouTube, Kick, Discord `3vH2u7pme5`) passent. `!permit` autorise un lien.
- Les insultes suivent trois paliers, mémorisés 30 jours dans `data/vulgar-strikes.json` : avertissement, timeout de 5 minutes, puis ban. Le journal `logs/moderation.log` note qui, quelle règle et quelle action, sans recopier le mot.
- Deux minutes après le début de chaque live, le bot envoie une fois le texte de `regles.example.txt`. `!regles` renvoie le même texte. L’identifiant du live est retenu dans `data/greeting.json` : un redémarrage pendant ce live ne renvoie pas le message. Le délai est `delay_seconds` dans `greeting.example.json`.
- EventSub envoie un message pour les follows, les abonnements, les réabonnements, les gifts, les raids et les bits. Un raid lance aussi un `/shoutout`.
- `!uptime`, `!followage`, `!so pseudo`, `!titre` et `!jeu`. Sans argument, `!titre` et `!jeu` affichent la valeur actuelle. Avec un argument, un mod peut la changer.
- `!relais on` et `!relais off` coupent ou ouvrent le relais du chat TikTok Live de `@zaeldryk`. Le format est `🎵 pseudo : message`. Si TikTok bloque la connexion, le bot Twitch continue.

Les réponses des commandes acceptent `{user}`, `{args}` et `{channel}`.

## Créer le compte bot

1. Crée un compte Twitch neuf, par exemple `zaeldrykbot`. Ne réutilise pas le compte `zaeldryk`.
2. Active la vérification e-mail et la 2FA.
3. Sur la chaîne `zaeldryk`, en étant broadcaster, tape `/mod zaeldrykbot` dans le chat. Sans ce grade, les timeouts et les shoutouts ne marchent pas.
4. Note le login exact. Il ira dans `TWITCH_BOT_LOGIN`.

## Créer l’application Twitch

1. Ouvre [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps) avec le compte qui possédera l’application.
2. Crée une application. Catégorie : Chat Bot.
3. OAuth Redirect URL : `http://localhost:17563/callback`
4. Copie le Client ID et génère un Client Secret. Ils vont dans `.env`, jamais dans le chat ni dans git.

## Obtenir le jeton

Sur ta machine, dans ce dossier :

```bash
cp .env.example .env
chmod 600 .env
```

Écris seulement `TWITCH_CLIENT_ID` et `TWITCH_CLIENT_SECRET` dans `.env`. Puis :

```bash
python3 scripts/get_token.py --flow code
```

Ouvre le lien affiché **en étant connecté au compte bot**. Le script écrit `TWITCH_BOT_ACCESS_TOKEN` et `TWITCH_BOT_REFRESH_TOKEN` dans `.env` et ne les affiche pas.

Si le flux par code est refusé, utilise :

```bash
python3 scripts/get_token.py --flow device
```

Va sur [twitch.tv/activate](https://www.twitch.tv/activate) avec le compte bot et saisis le code affiché.

Récupère ensuite l’identifiant numérique du compte bot (Helix `GET /users?login=`) et mets-le dans `TWITCH_BOT_USER_ID`. `TWITCH_BROADCASTER_ID` de zaeldryk est déjà `426411773` dans l’exemple.

## Déployer plus tard sur le VPS

À faire seulement après avoir vérifié le `.env` en local. Ne lance pas le service avant ça.

```bash
cd /home/ubuntu/zaeldryk
python3 -m venv venv
./venv/bin/pip install -r twitch-bot/requirements.txt
cp twitch-bot/.env.example twitch-bot/.env
chmod 600 twitch-bot/.env
```

Copie le dossier `Apps/TwitchXLive/zaeldryk/twitch-bot` vers `/home/ubuntu/zaeldryk/twitch-bot` s’il n’y est pas déjà. Colle les jetons dans ce `.env`. Puis :

```bash
sudo cp twitch-bot/systemd/zaeldryk-twitchbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-twitchbot.service
```

Le journal du bot est `twitch-bot/logs/bot.log`. Le service redémarre tout seul.

## Migrer depuis WizeBot

À exporter depuis le tableau WizeBot, ou à copier depuis le chat, avant de couper WizeBot :

- les commandes personnalisées et leur texte
- les timers (message, intervalle)
- la liste des mots interdits
- les exceptions de liens, s’il y en a
- les réglages de spam que tu veux garder

Reporte les commandes dans `data/commands.json` (créé au premier lancement à partir de l’exemple), les timers dans `data/timers.json`, les mots dans `data/moderation.json`.

Ce bot ne reprend pas les points, les duels, les quotes, les giveaways ni le song request. Les annonces de live Discord restent gérées par l’autre service Zaeldryk.

Coupe WizeBot seulement quand ce service est démarré et qu’un mod a testé `!discord` et `!commandes`.

## Limites

- Le bot doit être modérateur de `zaeldryk`.
- Un raid envoie le message même si le shoutout Helix est refusé (délai Twitch de 2 minutes entre deux shoutouts).
- Le relais TikTok dépend du site TikTok. S’il bloque, seul le relais s’arrête.
- `!permit` autorise un seul message avec lien, pendant 60 secondes. Cet état n’est pas gardé après un redémarrage.
- Les strikes de timeout redescendent après 30 minutes sans incident.
