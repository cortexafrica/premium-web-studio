# Direction artistique : ce qui distingue un site « à 10 000 $ »

## Sommaire
1. Ce que le client paie vraiment
2. Plan de direction en deux passes
3. Les réflexes génériques à éviter
4. Typographie
5. Bible visuelle pour les images générées
6. Niveaux de mouvement
7. Structures par type de page
8. Autocritique avant livraison

---

## 1. Ce que le client paie vraiment

Un site cher ne se reconnaît pas à la quantité d'effets. Il se reconnaît à :

- **Un point de vue** : des choix de couleur, de typographie et de mise en page qui viennent du sujet (la matière du produit, le quartier du restaurant, le métier du client), pas d'un modèle.
- **Un moment mémorable, un seul** : la séquence d'ouverture, une révélation du produit, une typographie monumentale. Tout le reste est calme et discipliné.
- **Des vrais contenus** : photos fidèles, textes précis, preuves réelles. Un texte générique rend un beau design banal.
- **La finition invisible** : alignements exacts, rythme vertical régulier, états de survol et de focus, chargement soigné, rendu mobile pensé et pas seulement « responsive ».
- **La vitesse** : un site lent paraît bon marché, quel que soit son esthétique.

## 2. Plan de direction en deux passes

**Passe 1 : écrire le plan** dans `studio/brief.md` (section « Direction ») :

- **Couleur** : 4 à 6 valeurs hexadécimales nommées par leur rôle (fond, texte, accent, surface, ligne). Partir de `extract_palette.py` quand une photo ou un logo existe, puis ajuster pour le contraste.
- **Typographie** : une ou deux familles, leurs rôles, l'échelle (tailles clamp), graisses et interlignage.
- **Mise en page** : un concept en une phrase + un croquis ASCII du héros et de deux sections. Préciser l'alignement (gauche, centré, asymétrique).
- **Mouvement** : niveau choisi (section 6) et le moment mémorable.
- **Principes** : 3 règles propres à ce projet (ex. « la matière du cuir est toujours en gros plan », « aucune couleur hors palette dans les photos »).

**Passe 2 : confronter le plan au brief.** Pour chaque axe, demande-toi si tu aurais proposé la même chose pour n'importe quel projet voisin. Si oui, c'est un défaut, pas un choix : révise-le et note ce qui a changé et pourquoi. Ne code qu'après cette revue.

## 3. Les réflexes génériques à éviter

Ces traits ne sont pas interdits quand le brief les demande explicitement. Ils sont à éviter quand ils arrivent par défaut :

- Fond crème chaud avec titre serif contrasté et accent terracotta.
- Fond presque noir avec un seul accent vert acide ou vermillon.
- Mise en page « journal » : filets fins partout, colonnes denses, zéro arrondi.
- Kit SaaS : contenu découpé en cartes identiques arrondies, même ombre grise sous chacune, dégradés décoratifs.
- Habillage de modèle : petit label en capitales espacées au-dessus de chaque titre, métadonnées séparées par des points médians, flèche « → » ajoutée à chaque lien, police monospace pour de petites étiquettes.
- Un mot du titre mis en italique ou en couleur pour « faire design ».
- Numéros 01 / 02 / 03 sur des contenus qui ne sont pas une séquence.
- Chaque section qui apparaît en glissant vers le haut au défilement.
- Chiffres ronds inventés (« +10 000 clients satisfaits ») et témoignages fictifs.

## 4. Typographie

- Une famille bien choisie vaut mieux que deux banales. Si deux familles : clairement différentes (ex. une grotesque expressive pour les titres, une humaniste lisible pour le texte).
- Sources libres fiables : Google Fonts / Fontsource. Pour une police payante, vérifier que le client a la licence web.
- Auto-héberger en woff2, sous-ensemble latin étendu si le français est la langue principale (accents), `font-display: swap`, une seule précharge (la police du titre héros).
- **Prendre le bon sous-ensemble, et le vérifier.** La CSS de Google Fonts renvoie plusieurs `@font-face` pour une même famille — latin, latin-ext, cyrillique, grec, vietnamien — chacun avec son URL et sa `unicode-range`. Copier la mauvaise donne un fichier qui se télécharge sans erreur et ne couvre presque aucune lettre : la page tombe en police système et seuls les rares caractères présents sortent dans la vraie fonte. Déclarer chaque sous-ensemble avec **sa** `unicode-range`, comme le fait Google, et ne précharger que le latin.
- Le contrôle : `check_release.py` mesure, caractère par caractère, si la famille déclarée s'applique vraiment. Il bloque au-delà de 30 % de caractères non couverts.
- Longueur de ligne < 75 caractères pour le texte courant, interlignage 1,5–1,65 ; les titres très grands en interlignage serré (0,95–1,1) et léger resserrement des lettres.
- La typographie peut être l'élément mémorable : taille monumentale, coupe inattendue, composition du titre avec l'image.

## 5. Bible visuelle pour les images générées

Avant toute génération, écris une **bible visuelle** de 3 à 5 lignes, réutilisée mot pour mot dans chaque prompt d'image et de vidéo. C'est ce qui rend un ensemble d'images cohérent.

```
Lumière : <ex. lumière rasante de fin d'après-midi, ombres longues et douces>
Palette : <couleurs de la direction, en mots et hex>
Matière et texture : <ex. grain pellicule léger, surfaces mates, pas de brillance plastique>
Optique et cadrage : <ex. 50 mm, faible profondeur de champ, cadrages centrés et frontaux>
Ambiance : <3 mots>
Exclusions : pas de texte incrusté, pas de logo inventé, pas de filigrane, mains et visages anatomiquement corrects
```

Nommer un univers de réalisateur ou de photographe peut transformer un rendu générique ; préfère décrire les caractéristiques visibles (lumière, cadrage, rythme) plutôt que de viser l'imitation d'une œuvre précise.

## 6. Niveaux de mouvement

| Niveau | Description | Quand |
|---|---|---|
| 0 — Éditorial | Aucune animation automatique, micro-interactions seulement | Contenu dense, marché data léger strict, marque sobre |
| 1 — Révélation unique | Une séquence d'entrée orchestrée au chargement, le reste statique | La plupart des sites vitrines et services |
| 2 — Héros cinématique | Une séquence pilotée par le défilement dans le héros, sections classiques ensuite | Lancement produit, marque premium, portfolio |
| 3 — Film défilant | Plusieurs scènes enchaînées sur toute la page | Campagne, produit phare, événement — budget et public desktop solides |

Le mouvement qui répond à une action (ouvrir, ajouter, confirmer) est toujours bienvenu. Le mouvement automatique sert à attirer l'attention une fois, pas à décorer chaque section.

## 6b. Une animation ne doit jamais pouvoir retenir du contenu

Une apparition au défilement masque du texte en attendant un signal. Si le
signal n'arrive pas, le texte n'arrive pas. **Le visiteur ne voit pas une
animation ratée, il voit une page trouée** — et il ne saura jamais ce qu'il a
manqué.

Quatre règles, toutes tirées de défauts constatés sur un site en production.
Les deux dernières viennent du **correctif lui-même** : le
filet de sécurité était plus dangereux que l'animation.

**1. Le CSS ne masque jamais de lui-même.** Le piège d'origine : la feuille de
style posait `opacity: 0` dès son chargement, et le JavaScript, arrivé bien plus
tard, devait révéler. Entre les deux la page était trouée ; si le script ne
tournait pas, elle le restait.

> Le sélecteur doit exiger une classe posée **par le script**, après vérification
> qu'il peut la retirer : `.js-reveal [data-reveal]:not([data-revealed])`. Pas de
> script, pas de masquage. La page perd son animation, jamais son contenu.

**2. Masquer avant la première peinture.** Avec un effet monté après le rendu
(`useEffect`), la page est peinte visible, puis masquée : un clignotement à
chaque chargement, et il se voit surtout là où l'on voulait aider, sur un
téléphone lent. `useLayoutEffect` s'exécute avant la peinture. Mesure : à 16 ms,
les blocs hors écran doivent déjà être à `opacity: 0`.

**3. Un observateur d'intersection ne suffit pas.** Un doigt qui lance la page
fait franchir l'écran à un bloc **entre deux observations** : aucun seuil n'est
signalé, le bloc n'est jamais révélé, et il reste vide pour toujours une fois
dépassé. Constaté : le bouton vidéo, à 5 768 px au-dessus de l'écran, encore
invisible.

> Ajouter un balayage au défilement, cadencé sur `requestAnimationFrame`, qui
> révèle tout ce qui est entré dans l'écran **ou l'a dépassé**. Il ne remplace
> pas l'observateur, qui donne l'animation au bon moment ; il garantit qu'aucun
> bloc ne reste en arrière.

**4. Un délai de secours inconditionnel tue l'effet.** Le premier filet révélait
tout après 1,2 s. Sur une connexion lente, il révélait la page entière avant que
le visiteur ait eu le temps de défiler : l'effet n'existait nulle part où il
aurait été visible. **Un filet qui attrape tout le monde n'est plus un filet,
c'est un plafond.**

> Le filet ne doit se déclencher que si l'observateur est réellement mort. Un
> observateur d'intersection rappelle toujours une première fois, pour chaque
> élément observé, qu'il soit à l'écran ou non. Ce premier rappel désarme le
> filet.

**Les cinq cas à éprouver avant de livrer une apparition au défilement**, et
aucun n'est théorique — chacun a échoué au moins une fois :

| Cas | Ce qu'on exige |
|---|---|
| Au chargement, sans défiler | les blocs hors écran sont masqués — l'effet existe |
| Saut direct en bas de page | aucun bloc masqué |
| Défilement rapide par à-coups | aucun bloc masqué |
| Observateur neutralisé | aucun bloc masqué — le filet a rendu la page |
| `prefers-reduced-motion` | aucun bloc masqué |

**Et la règle qui les résume** : sur toute animation qui masque, la question
n'est pas « est-ce que ça s'affiche bien ? » mais **« que voit quelqu'un pour
qui le mécanisme ne s'est pas déclenché ? »**. Si la réponse est « moins de
contenu », le mécanisme est à refaire, quelle que soit sa beauté quand il
fonctionne.

## 7. Structures par type de page

Adapter, ne pas remplir mécaniquement. Chaque section doit répondre à une question du visiteur.

- **Lancement produit** : héros (produit en majesté) → le problème ou le désir → le produit en détail (matière, usage) → preuves → offre et prix → objections (FAQ) → action finale.
- **Service local** (artisan, clinique, avocat) : héros avec promesse + moyen de contact immédiat → services → réalisations avant/après → équipe et lieu → avis → zone et horaires → contact.
- **Restaurant / hôtel** : héros ambiance → carte ou chambres signature → lieu et histoire → réservation → accès et horaires.
- **Portfolio / créatif** : héros qui est déjà une œuvre → 3 à 6 projets en profondeur → démarche → contact.
- **SaaS / app** : héros avec démonstration réelle → problème → comment ça marche (vraie séquence) → cas d'usage → preuves → tarifs → FAQ → essai.
- **Événement** : héros date + lieu + action → programme → intervenants → pratique → billetterie.
- **Immobilier** : héros visite du bien → points forts → plans et surfaces → quartier → prix et contact.

## 8. Autocritique avant livraison

Ouvre les captures de `review_site.py` et vérifie :

- Le moment mémorable est-il évident dans les 3 premières secondes, sur mobile aussi ?
- Le texte superposé est-il lisible sur **chaque** image de la séquence (pas seulement la première) ?
- Retire un accessoire : quel élément décoratif peut disparaître sans perte ? Retire-le.
- Chaque couleur, police et effet vient-il du plan ? Sinon, le supprimer ou mettre à jour le plan.
- La page ressemblerait-elle à un autre site généré si on changeait le nom de marque ? Si oui, identifier l'axe générique et le retravailler.
