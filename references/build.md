# Construire le site

## Sommaire
1. Choisir la cible
2. Template cinématique (Vite + React)
3. Next.js
4. Hébergement Higgsfield (`higgsfield website`)
5. Shopify
6. Règles de performance
7. SEO, partage et suivi

---

## 1. Choisir la cible

| Situation | Cible |
|---|---|
| Landing page ou one-page, livraison rapide, hébergement libre | Template `assets/cinematic-template` |
| Plusieurs pages, blog, SEO important, formulaires côté serveur | Next.js (App Router) avec le composant `ScrollSequence` porté |
| L'utilisateur veut héberger et déployer via Higgsfield | `higgsfield website` (React 19 + TanStack Start sur Cloudflare) |
| Page de marque ou de lancement pour une boutique Shopify existante | Section de thème Shopify, ou landing séparée qui renvoie vers les pages produit / le panier Shopify |

Si rien n'est précisé pour une landing page : template cinématique, déployé sur Vercel ou Cloudflare Pages.

## 2. Template cinématique (Vite + React)

```bash
cp -r <skill>/assets/cinematic-template <projet>
cd <projet> && npm install
python3 <skill>/scripts/video_to_frames.py --input ../studio/assets/video/clip-01.mp4 --out public/frames
npm run dev
```

Puis, dans l'ordre :
1. **`src/styles.css`** : réécrire les jetons depuis le plan de direction. Les valeurs fournies sont neutres exprès.
2. **`src/facts.json`** : copie de `studio/facts.json`. Les chiffres des textes et des visuels viennent de là, formatés par `src/lib/format.ts` (voir `facts.md`).
3. **`src/content.ts`** : remplir tous les textes depuis le brief et `copywriting.md`. Ajuster `from` / `to` de chaque temps fort pour qu'ils tombent sur les bonnes images de la séquence.
4. **`src/App.tsx`** : garder, retirer ou ajouter des sections selon la structure choisie (`art-direction.md` §7). Le template est un point de départ, pas une structure imposée.
5. **Polices, images, `og.jpg`, `index.html`** (titre, description, `theme-color`, `<noscript>`).
6. `npm run build` puis `scripts/check_budget.py dist` et `scripts/check_facts.py`.

Réglages de `ScrollSequence` :
- `scrollLength` : 1 écran de défilement par temps fort environ (3 à 6).
- `fit="contain"` quand le produit ne doit jamais être rogné.
- Placer les temps forts (`beats`) sur les zones calmes des images ; `position` = `start`, `center` ou `end`.

## 3. Next.js

- Copier `ScrollSequence.tsx`, `network.ts` et `smooth-scroll.ts` dans le projet ; ajouter `'use client'` en tête de `ScrollSequence.tsx` et du composant qui lance `startSmoothScroll`.
- Frames dans `public/frames`, manifest à `/frames/manifest.json`.
- Le texte des temps forts doit aussi exister dans le HTML rendu côté serveur (il l'est : les `beats` sont rendus dans le DOM).
- Métadonnées via l'API `metadata` de Next.js ; image de partage 1200×630.

## 4. Hébergement Higgsfield (`higgsfield website`)

Flux officiel (vérifier `higgsfield website --help`) :

```bash
higgsfield website categories                       # choisir la catégorie la plus proche
higgsfield website create --type website --category <slug> --subdomain <nom-du-site>
higgsfield website repo-access <website_id>         # URL du dépôt, branche, jeton git temporaire
git -c http.extraHeader="Authorization: token <token>" clone <repo_url> <slug>
cd <slug>
git config user.email "<email>" && git config user.name "<nom>"
# Modifier sous app/ — dépôt bun uniquement : bun install / bun add / bun run build
git add -A && git commit -m "initial build"
git -c http.extraHeader="Authorization: token <token>" push origin <branch>
higgsfield website deploy <website_id>              # à relancer après chaque modification
higgsfield website status <website_id>              # URL en ligne
```

Points d'attention :
- `--type website` pour un site indépendant ; `--type app` seulement si les visiteurs doivent se connecter avec Higgsfield et générer eux-mêmes.
- La stack est TanStack Start, pas Vite simple : porter `ScrollSequence` et le CSS dans `app/`, frames dans le dossier public du projet, et ne jamais modifier le fichier de routes généré.
- Ne jamais afficher le jeton git dans la conversation.
- `publish` rend le site visible dans le flux communautaire Higgsfield : ne le faire que si l'utilisateur le demande.

## 5. Shopify

Deux approches :

**Section de thème** (la page vit dans la boutique) :
- Créer `sections/cinematic-hero.liquid` avec schéma éditable (textes des temps forts, bouton, produit lié).
- Frames téléversées dans les fichiers Shopify (Contenu → Fichiers) ou dans `assets/` si peu nombreuses ; manifest adapté aux URL du CDN Shopify.
- Porter la logique de `ScrollSequence` en JavaScript natif (canvas + `IntersectionObserver` + position de défilement) : pas de React dans un thème.
- Bouton d'achat : formulaire `/cart/add` du thème, ou lien vers la fiche produit.

**Landing séparée** (template cinématique hébergé ailleurs) :
- Boutons vers les fiches produit ou vers `https://<boutique>/cart/<variant_id>:<quantité>` pour un panier pré-rempli.
- Garder le même nom de domaine si possible (sous-domaine) pour la confiance.

Si le Shopify AI Toolkit est installé, l'utiliser pour valider le Liquid et les requêtes GraphQL.

## 6. Règles de performance

Budgets par défaut (`check_budget.py`) : JS ≤ 220 Ko gzip, CSS ≤ 60 Ko gzip, poids initial ≤ 1,8 Mo, séquence desktop ≤ 12 Mo, séquence mobile ≤ 5 Mo, aucune image isolée > 350 Ko. Profil data léger : diviser les budgets de séquence par deux.

- Images : WebP ou AVIF, dimensions explicites (`width`/`height`), `loading="lazy"` sous la ligne de flottaison, `srcset` pour les grandes images.
- Vidéo en boucle (hors séquence) : `muted playsinline loop`, `preload="none"` ou `metadata`, poster obligatoire, fichier ≤ 2–3 Mo.
- Polices : woff2 auto-hébergées, 2 à 4 fichiers maximum.
- Pas de bibliothèque d'animation supplémentaire si GSAP est déjà là.
- Le premier écran doit être lisible avant que la séquence ne soit chargée (poster + titre).

## 7. SEO, partage et suivi

- Un seul `h1`, hiérarchie de titres logique, texte réel dans le HTML.
- Titre ≤ 60 caractères, description ≤ 155, image de partage 1200×630 (générée ou composée depuis une image clé, avec le nom de marque lisible).
- `lang` correct, favicon, `theme-color`.
- Données structurées quand c'est utile : `Product` (prix, disponibilité), `LocalBusiness` (adresse, horaires), `Event`.
- Suivi léger des clics sur l'action principale (outil choisi par l'utilisateur). Ne pas ajouter de script de suivi non demandé.
