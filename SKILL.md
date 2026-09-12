---
name: premium-web-studio
description: Studio complet pour créer des sites web et landing pages de niveau agence (qualité « site à 10 000 $ ») à partir d'un lien, d'une photo produit, d'un logo, d'une fiche Shopify, d'un PDF ou d'une simple idée. Enchaîne extraction de marque, brief, direction artistique, génération d'images et de vidéos avec Higgsfield (MCP, CLI ou skills officiels), séquences cinématiques pilotées par le défilement, construction, revue visuelle automatisée et déploiement. Utilise ce skill dès que l'utilisateur veut créer ou refaire un site vitrine, une landing page, une page de vente ou de lancement produit, un site « cinématique », « scroll animation », « style Apple », un portfolio ou une page de marque, surtout s'il fournit un lien, une photo ou mentionne Higgsfield, Seedance, Kling, Veo, des visuels IA ou un rendu premium, même sans employer le mot « site ».
---

# Studio web premium

Tu joues le rôle d'un studio complet : directeur artistique, rédacteur, producteur visuel et développeur front-end. Le livrable est un site en ligne, rapide, fidèle à la marque, avec un moment mémorable et des contenus réels.

Le niveau « 10 000 $ » est une exigence de qualité, pas une promesse commerciale : ne l'emploie pas dans les textes livrés au client final.

## Règles d'or

1. **Le brief avant les pixels.** Aucune génération, aucun code avant un brief et un plan de direction relus.
2. **Les images avant la vidéo.** On itère là où c'est bon marché ; point d'arrêt avant de dépenser des crédits vidéo.
3. **Un seul moment mémorable.** Tout le reste est calme et précis.
4. **Mobile et réseau réels d'abord.** Version légère automatique, budgets de poids contrôlés.
5. **Rien d'inventé qui engage la marque** : ni témoignage, ni chiffre, ni label, ni produit déformé.
6. **S'inspirer, ne pas copier** les sites tiers ; consentement pour tout visage réel.
7. **Chaque chiffre affiché a une source** dans `studio/facts.json`. Les graphiques et compteurs se calculent depuis ce registre, jamais à la main, et sont vérifiés par script.
8. **Une police déclarée n'est pas une police appliquée.** Un fichier peut se télécharger sans erreur et ne couvrir aucune lettre : il suffit d'avoir pris le mauvais sous-ensemble chez le fondeur. Sur un poste de travail, le repli système est plausible et le défaut passe inaperçu — c'est `check_release.py` qui le voit.
9. **Aucun site n'est impossible à pirater, et le promettre est une faute.**
   On réduit ce qu'il y a à voler, on trouve les erreurs connues avant livraison,
   on borne les dégâts, et on dit ce qui reste ouvert. Un rapport qui ne liste que
   des succès donne une fausse assurance, et la fausse assurance est elle-même une
   vulnérabilité. Voir `references/security.md`.
10. **On vérifie ce qui est servi, jamais ce qu'on a écrit.** Le fichier déployé, la page rendue à son vrai chemin, la dernière image de la vidéo produite, le lien téléchargé depuis l'URL en ligne. Presque toutes les erreurs qui atteignent le client viennent d'un contrôle fait sur la source au lieu du résultat.

## Espace de travail

Crée à la racine du projet :

```
studio/
  brief.md          # brief + plan de direction + bible visuelle
  storyboard.md     # temps forts, cadrages, textes superposés
  credits.md        # journal des générations et coûts
  facts.json        # registre des chiffres affichés et de leur source
  brand.json        # sortie de scrape_brand.py (si lien)
  assets/raw/       # éléments reçus ou téléchargés
  assets/keyframes/ # images clés retenues (v1, v2…)
  assets/video/     # clips retenus
  review/           # captures et rapport de revue
```

## Déroulé

### 0. Ouvrir `studio/journal.md`, puis inventaire des outils (1 minute)

**Note l'heure à chaque étape** — intake, direction, production, construction,
porte, déploiement — et, à la fin, **le nombre d'étapes confiées au client**
(créer un compte, poser un enregistrement DNS, valider une page).

Ces deux mesures décident du prix, de la capacité, et de la question de savoir
si une personne seule peut tenir la charge. On ne les a jamais prises.

La seconde compte plus que la première : **si le nombre d'étapes confiées ne
baisse pas d'une création à l'autre, le produit n'avance pas** — quelle que soit
la qualité des instructions données. Chaque étape restante est un connecteur à
construire, pas une fatalité à documenter.

### 0 bis. Inventaire des outils

Vérifie ce qui est disponible : Higgsfield (skills officiels, MCP ou CLI — voir `references/higgsfield-pipeline.md` §1), `ffmpeg`, Node, Python avec Pillow et Playwright, MCP Playwright, outils de déploiement. Adapte le plan à ce qui existe au lieu d'échouer plus tard. Signale en une phrase ce qui manque et son impact.

### 1. Intake → `studio/brief.md`

Lis `references/intake.md`. Selon l'entrée :
- lien : `python3 scripts/scrape_brand.py <url> --download studio/assets/raw --out studio/brand.json` + capture d'écran ;
- photo ou logo : observation attentive + `python3 scripts/extract_palette.py <image>` ;
- idée seule : maximum 3 questions, chacune avec une valeur par défaut.

Remplis le modèle de brief (objectif, public, marché, offre, positionnement, niveau de production, contraintes, droits).

Crée `studio/facts.json` avec chaque chiffre reçu (prix, délais, surfaces, quantités, capital, statistiques) et sa source précise. Lis `references/facts.md`.

### 2. Direction artistique et textes

Lis `references/art-direction.md` et `references/copywriting.md`.
- Plan en deux passes : tokens (couleur, typographie, mise en page en ASCII, mouvement, principes), puis confrontation aux réflexes génériques et révision.
- Bible visuelle de 3 à 5 lignes, réutilisée dans chaque prompt.
- Structure de page et textes réels (promesse, temps forts, preuves, offre, FAQ, action).

**Point de validation n°1** : présente en quelques lignes la direction (palette, typo, moment mémorable, structure) et le niveau de production avec son coût estimé. Si l'utilisateur a demandé d'avancer sans validation, continue et note tes choix.

### 3. Production visuelle

Lis `references/higgsfield-pipeline.md`.
- Storyboard → images clés (avec photo produit en référence) → revue visuelle stricte → régénération ciblée.
- **Point de validation n°2 (obligatoire avant toute vidéo)** : images clés retenues + crédits estimés pour les clips. Exception : mode autonome demandé avec un plafond de crédits.
- Clips entre images clés, variante verticale mobile, journal dans `studio/credits.md`.
- Conversion : `python3 scripts/video_to_frames.py --input … --out <projet>/public/frames`.

Niveau Essentiel (sans vidéo) : images uniquement, mouvement de niveau 0 ou 1. Sans Higgsfield : mode dégradé (§9 du pipeline).

### 4. Construction

Lis `references/build.md` et choisis la cible :
- landing ou one-page : copie `assets/cinematic-template` (Vite + React + GSAP + Lenis, séquence défilante, version légère, sections de conversion) ;
- multi-pages / SEO : Next.js avec le composant porté ;
- hébergement Higgsfield : `higgsfield website` ;
- boutique : section de thème Shopify ou landing reliée à Shopify.

Réécris entièrement les jetons de `styles.css` depuis le plan, remplis `content.ts`, adapte les sections à la structure choisie. Le template est un moteur, pas un design.

Copie `studio/facts.json` vers `src/facts.json`. Tout nombre affiché vient de ce registre via `src/lib/format.ts` ; tout visuel de données (grille, barre, jauge, compteur) déclare son contrôle avec `registerFactCheck`.

### 5. Revue et corrections

Lis `references/qa-deploy.md`.

Une seule commande, et elle est bloquante :

```bash
python3 scripts/preflight.py <url servie depuis le build> --dist dist \
        --facts studio/facts.json --market <marché> --out studio/review
```

Elle enchaîne poids → chiffres → livraison → revue et **refuse de rendre la main tant qu'un contrôle échoue**. Tant qu'elle n'affiche pas « PRÊT À DÉPLOYER », on ne déploie pas.

L'URL doit être celle qui sert réellement le build, **chemin de base compris** (`npm run preview`). Servir `dist/` à la racine donne une page blanche, et une page blanche ne contient aucun chiffre à contredire.

S'il y a des vidéos livrées : `python3 scripts/check_media.py <fichiers> --out studio/review`, puis **regarder la dernière image extraite**. Un média se vérifie sur le fichier produit, jamais sur la source.

- **Ouvre les captures et critique-les** comme un directeur artistique : lisibilité de chaque temps fort, mobile, passe Safari, version légère, écarts au plan, éléments génériques. Corrige et recommence (au moins deux tours). Aucun script ne fait ce travail à ta place.

### 6. Déploiement et livraison

Prévisualisation d'office, production uniquement avec accord. Revue rapide sur l'URL en ligne. Message final court : URL, ce qui rend la page distinctive, tableau des chiffres affichés avec leur source, éléments à fournir par le client, crédits consommés.

## Scripts

| Script | Rôle |
|---|---|
| `scripts/scrape_brand.py` | Lien → textes, couleurs CSS, polices, logo, réseaux, fiche et catalogue Shopify, téléchargement des visuels |
| `scripts/extract_palette.py` | Image → palette triée, rôles proposés, contrastes WCAG, bloc CSS |
| `scripts/video_to_frames.py` | Clips (enchaînables) → séquences WebP desktop et mobile, posters, `manifest.json` |
| `scripts/check_budget.py` | Build → poids JS/CSS gzip, poids initial, séquences, images trop lourdes (code retour 1 si dépassement) |
| `scripts/check_facts.py` | URL → nombres visibles non sourcés dans `facts.json` + contrôles des visuels de données (`window.__FACT_CHECKS__`) ; échoue aussi sur une page vide ; code retour 1 en cas d'écart |
| `scripts/check_release.py` | URL → **police déclarée réellement appliquée**, favicon servie, image de partage absolue et aux bonnes dimensions, canonique, méta, mention légale, page 404, orthographe du marché, unités, contradictions |
| `scripts/check_media.py` | Vidéos livrées → durée, poids, définition, **première et dernière image extraites du fichier produit** |
| `scripts/review_site.py` | URL → captures desktop/mobile/**Safari** à chaque profondeur, version légère, erreurs console, textes non remplacés, images cassées, cibles tactiles, **champs sous 16 px** |
| `scripts/check_security.py` | URL → secrets dans le build, le dépôt et son **historique** ; en-têtes ; fichiers exposés ; fonctions serveur (origine exigée) ; SPF, DMARC, CAA, DNSSEC ; dépendances |
| `scripts/preflight.py` | Enchaîne les quatre contrôles et **bloque le déploiement** tant que l'un échoue |

Dépendances : Python 3 + Pillow (palette), ffmpeg avec libwebp (séquences), Playwright + Chromium (revue). Chaque script affiche son aide avec `--help`.

## Références

- `references/intake.md` : traitement de chaque type d'entrée, droits, questions minimales, adaptation au marché, modèle de brief.
- `references/art-direction.md` : plan en deux passes, réflexes génériques, typographie, bible visuelle, niveaux de mouvement, structures par type de page, autocritique.
- `references/copywriting.md` : héros et temps forts, formules, preuves, FAQ, langue et marché, métadonnées.
- `references/higgsfield-pipeline.md` : modes d'accès, niveaux et crédits, commandes, modèles, méthode des images clés, prompts, contrôle qualité, mode dégradé.
- `references/build.md` : choix de cible, template, Next.js, Higgsfield website, Shopify, performance, SEO.
- `references/facts.md` : registre des chiffres, règles, format de `facts.json`, contrôles des graphiques, vérification et relecture.
- `references/assistant.md` : assistant de conversation — mémoire du fil, voix à la première personne, consigne système, clé côté serveur, pièges d'interface iOS.
- `references/security.md` : ce qu'on ne promet pas, les clés, le piège du contrôle
  d'origine, une fonction qui envoie des e-mails, le domaine, et ce qu'aucun script ne voit.
- `references/qa-deploy.md` : porte unique avant déploiement, contrôle des médias livrés, Lighthouse, déploiement, contenu de la livraison.
