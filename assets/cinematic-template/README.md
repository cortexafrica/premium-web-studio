# Template « cinematic-site »

Landing page en Vite + React + TypeScript, avec une séquence d'images pilotée par le défilement (GSAP ScrollTrigger + Lenis), une version légère automatique et des sections de conversion.

## Démarrage

```bash
npm install
python3 <skill>/scripts/video_to_frames.py --input ../studio/assets/video/clip-01.mp4 --out public/frames
npm run dev
```

## À remplir avant livraison

1. `src/content.ts` : tous les textes, depuis `studio/brief.md` (aucun crochet ne doit rester).
2. `src/styles.css` : réécrire les jetons (couleurs, polices, échelle) selon le plan de direction artistique.
3. `public/images/` : image de l'offre (`offer.webp`), image de partage `public/og.jpg` (1200×630).
4. `index.html` : titre, description, balises Open Graph, `theme-color`, contenu `<noscript>`.
5. Polices : auto-hébergées en woff2 (Fontsource ou fichiers fournis), une seule précharge.

## Comportements intégrés

- **Mobile** : séquence verticale dédiée (`manifest.mobile`), chargée à la place du desktop.
- **Chargement progressif** : 1 image sur 16 d'abord, puis affinage ; l'image la plus proche s'affiche en attendant.
- **Version légère** : image fixe + textes empilés si mouvement réduit, économiseur de données, réseau lent (Chromium), ou `?lite=1`.
- **Accessibilité** : canvas avec `role="img"` et description, un seul `h1`, focus visible, cibles de 44 px.
