# Intake : du lien, de la photo ou de l'idée au brief

## Sommaire
1. Traiter chaque type d'entrée
2. Droits et consentement
3. Questions minimales
4. Adapter au marché
5. Modèle `studio/brief.md`

---

## 1. Traiter chaque type d'entrée

| Entrée | Actions | Ce qu'on en tire |
|---|---|---|
| **Site de la marque** (l'utilisateur en est propriétaire) | `scripts/scrape_brand.py <url> --download studio/assets/raw --out studio/brand.json` + capture d'écran desktop et mobile (MCP Playwright, `review_site.py` ou captures fournies) | Nom, promesse actuelle, couleurs CSS, polices, logo, ton, réseaux, images réutilisables |
| **Produit Shopify** (`/products/…`) | Même script : il lit la fiche produit publique (`.json`) et télécharge les photos | Titre, description, options, prix, photos officielles, type de produit |
| **Boutique Shopify entière** | `scrape_brand.py <url> --catalog` | 12 produits phares pour choisir le héros de la page |
| **Photo produit** | L'observer attentivement (forme, matière, étiquette, défauts), `scripts/extract_palette.py`, détourage si utile (`image_background_remover` via Higgsfield) | Palette, matières, angle héros, contraintes de fidélité |
| **Logo** | `extract_palette.py`, observer la forme et le caractère typographique | Couleurs de marque, tempérament (géométrique, manuscrit, massif…) |
| **Site d'inspiration / concurrent** | Captures + analyse de la structure et du rythme | Principes seulement (voir section 2) |
| **Lien Instagram / TikTok** | Souvent bloqué au robot : demander 3 à 6 captures ou les meilleures photos | Univers visuel réel, produits vedettes, ton |
| **PDF, menu, plaquette, présentation** | Lire le fichier | Offre, prix, arguments, vocabulaire du métier |
| **Idée en texte seul** | Questions minimales (section 3), puis proposer un concept | Tout est à construire : annoncer qu'on part d'une proposition |

Si un script échoue (site protégé, JavaScript obligatoire), passe par une capture d'écran et une lecture visuelle. Ne bloque jamais le projet sur l'extraction automatique.

Après l'intake, écris ce que tu as **observé** (faits) séparément de ce que tu **proposes** (interprétations). Le brief doit rester vérifiable.

## 2. Droits et consentement

- **Contenus de la marque de l'utilisateur** : réutilisables.
- **Site d'un tiers pris en inspiration** : reprendre des principes (structure, rythme, niveau de finition), jamais le logo, les photos, les textes, les illustrations ni une copie reconnaissable de la mise en page. Le nom de la marque tierce n'apparaît nulle part dans le livrable.
- **Personnes réelles** : générer ou entraîner un visage (Soul ID) uniquement avec des photos que la personne a fournies et accepte de voir utilisées. Jamais de célébrité ni de personne identifiable sans accord.
- **Témoignages, chiffres, labels, certifications, logos clients** : uniquement s'ils sont fournis ou vérifiables. Sinon, laisser un emplacement marqué et le signaler au moment de la livraison.
- **Produits générés par IA** : le produit montré doit rester fidèle au produit réel (forme, couleur, étiquette). Une image trompeuse sur un produit vendu est un problème commercial et légal, pas un détail esthétique.

## 3. Questions minimales

Pose au maximum 3 questions, uniquement si la réponse change le livrable et n'est pas déductible des éléments reçus. Propose une valeur par défaut dans chaque question pour que l'utilisateur puisse répondre « ok ».

1. **Action attendue** : que doit faire le visiteur ? (commander, réserver, écrire sur WhatsApp, laisser son email, appeler)
2. **Public et marché** : qui, où, dans quelle langue, sur quel appareil principalement ?
3. **Niveau et budget** : Essentiel, Signature ou Cinéma (voir `higgsfield-pipeline.md`), et crédits disponibles.

Tout le reste (ton, sections, palette, animation) se propose dans le brief plutôt que de se demander.

## 4. Adapter au marché

Le marché change la page autant que la marque. Vérifie et note dans le brief :

- **Langue et registre** : tutoiement ou vouvoiement, termes locaux, devise et format de prix.
- **Moyens d'action attendus** : checkout carte, paiement à la livraison, mobile money, WhatsApp, appel, prise de rendez-vous. Dans de nombreux marchés d'Afrique francophone par exemple, un bouton WhatsApp ou une commande avec paiement à la livraison convertit mieux qu'un formulaire de paiement en ligne : ne pas l'imposer, mais le demander.
- **Réseau et appareils** : mobile majoritaire, data coûteuse ou lente → profil de performance « data léger » (séquences plus courtes, version légère par défaut sur réseau lent, poids initial réduit).
- **Preuves qui rassurent localement** : adresse physique, numéro joignable, délais de livraison réels, avis clients vérifiables, visages de l'équipe.

## 5. Modèle `studio/brief.md`

```markdown
# Brief — <Nom du projet>

## Sources
- Éléments reçus : <lien, photos, fichiers>
- Observé : <faits extraits : couleurs, polices, textes, produits>

## Objectif
- Action principale : <verbe + destination du bouton>
- Action secondaire : <facultatif>
- Mesure de succès : <ex. clics WhatsApp, commandes, emails>

## Public
- Qui : <description concrète>
- Marché, langue, devise : <…>
- Appareil et réseau dominants : <…> → profil performance : standard | data léger

## Offre
- Produit ou service : <…>
- Prix / conditions : <…>
- Preuves disponibles : <témoignages réels, chiffres, labels> | à fournir

## Positionnement
- Promesse en une phrase : <…>
- Ce qui la rend crédible : <…>
- Ton : <3 adjectifs + 1 à éviter>

## Niveau de production
- Niveau : Essentiel | Signature | Cinéma
- Crédits disponibles / estimés : <…>
- Hébergement visé : <Vercel, Cloudflare, Higgsfield, Shopify…>

## Contraintes
- Imposé : <couleurs, logo, mentions légales, délais>
- Interdit : <…>
- Droits : <ce qui est réutilisable, ce qui ne l'est pas>
```
