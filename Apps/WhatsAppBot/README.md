# Bot WhatsApp

Bot Node.js (Baileys) : scanne un QR une fois, puis répond aux commandes et aux mots-clés.

## Démarrage

```powershell
cd C:\Users\nacim\Documents\projet\Apps\WhatsAppBot
copy .env.example .env
npm install
npm start
```

1. Un QR s’affiche dans le terminal.
2. Sur le téléphone : **WhatsApp → Paramètres → Appareils liés → Lier un appareil**.
3. Envoie `!help` au numéro connecté depuis un autre téléphone.

Si le QR est illisible sous Windows, mets ton numéro dans `.env` :

```
PAIRING_NUMBER=33612345678
```

Puis relance `npm start` et saisis le code à 8 chiffres dans WhatsApp.

## Commandes

| Commande | Action |
|----------|--------|
| `!help` | Liste des commandes |
| `!ping` | Test de réponse |
| `!info` | Infos de la conversation |
| `!heure` | Date et heure (Paris) |
| `!echo texte` | Répète le texte |

Les réponses auto (bonjour, merci, etc.) se règlent dans `config.json`.

## Config

- `config.json` — nom, préfixe, groupes, réponses auto
- `.env` — `OWNER_NUMBER` (optionnel), `PAIRING_NUMBER` (optionnel)

Le dossier `auth_info/` contient la session. Ne le partage pas. Pour reconnecter un autre numéro, supprime-le et relance.

## À savoir

Ce bot utilise le protocole WhatsApp Web (non officiel). Prends un **numéro dédié**, pas ton WhatsApp perso. Pour un usage business long terme, l’API Cloud officielle Meta est plus adaptée.
