# Wado-Osny — refonte locale

Refonte moderne du site [wado-osny.fr](https://wado-osny.fr/) : Next.js 16, React 19, Tailwind CSS 4, TypeScript.

## Lancer en local

```bash
cp .env.example .env.local
npm install
npm run dev
```

Ouvrir [http://localhost:3000](http://localhost:3000).

Admin club : [http://localhost:3000/dojo-admin](http://localhost:3000/dojo-admin)  
(mot de passe = `ADMIN_PASSWORD` du `.env.local` au premier lancement)

## Contenu éditable (admin)

Événements, médiathèque, horaires, tarifs, instructeurs, club/contact.  
Stockage : `data/*.json` + `uploads/` (voir [docs/admin-vps.md](docs/admin-vps.md)).

## Pages

- Accueil, Wado Ryu, TSYR, Instructeurs, Horaires, Tarifs, Calendrier, Médiathèque, Contact
- Historique, Mentions légales, Confidentialité
