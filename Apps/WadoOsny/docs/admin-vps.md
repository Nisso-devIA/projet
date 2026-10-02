# Persistance VPS — admin Wado

Après déploiement du code Next sur `/var/www/wado-osny` :

1. Créer les dossiers persistants (hors overwrite tarball si besoin) :
   - `/var/www/wado-osny/data`
   - `/var/www/wado-osny/uploads`
2. Dans `.env` / PM2 :
   - `ADMIN_PASSWORD=...` (bootstrap une fois)
   - `ADMIN_SECRET=` (32+ caractères)
   - `UPLOADS_DIR=/var/www/wado-osny/uploads`
3. Nginx : le site Next sert déjà `/uploads/*` via la route App Router.
   Optionnel : servir `/uploads/` en static depuis le dossier (comme Miina).
4. Admin : `https://wado-osny.fr/dojo-admin`
5. Rate-limit login recommandé côté nginx sur `/dojo-admin/login`.
