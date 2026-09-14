# Pipeline de production visuelle avec Higgsfield

## Sommaire
1. Détecter le mode d'accès
2. Niveaux de production et budget
3. Commandes CLI utiles
4. Choisir les modèles
5. Méthode des images clés
6. Formules de prompts
7. Fidélité produit et contrôle qualité
8. Du clip au site
9. Mode dégradé sans Higgsfield

---

## 1. Détecter le mode d'accès

Vérifie dans cet ordre et utilise le premier disponible :

1. **Skills officiels Higgsfield installés** (`higgsfield-generate`, `higgsfield-product-photoshoot`…) : les suivre pour la génération, ils connaissent les paramètres à jour.
2. **Serveur MCP Higgsfield** : outils dont le nom contient `higgsfield` dans la liste des outils. Lire leur schéma avant le premier appel ; ne jamais deviner les noms de paramètres.
3. **CLI** : `higgsfield version` répond. Vérifier la session avec `higgsfield account` (solde de crédits). Si « Session expired » ou « Not authenticated », demander à l'utilisateur de lancer `higgsfield auth login` et attendre.
4. **Rien** : proposer l'installation (MCP : `claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp` puis `/mcp` pour s'authentifier ; ou CLI : `npm install -g @higgsfield/cli`), ou basculer en mode dégradé (section 9).

Ne demande jamais de clé API dans la conversation. Le MCP et la CLI s'authentifient par le navigateur.

## 2. Niveaux de production et budget

| Niveau | Contenu généré | Usage |
|---|---|---|
| **Essentiel** | 4 à 10 images (héros, sections, image de partage), zéro vidéo | Budget serré, marché data léger, site de service |
| **Signature** | Images + 1 à 2 clips (héros en séquence ou boucle vidéo courte) + variante verticale mobile | Cas le plus fréquent pour un lancement ou une marque premium |
| **Cinéma** | 4 à 6 images clés → 3 à 5 clips enchaînés, desktop + mobile | Campagne, produit phare, public desktop solide |

Discipline de crédits :

- **Estimer avant de générer** : `higgsfield generate cost …` quand la commande le permet, sinon générer une seule image test et lire la consommation dans `higgsfield account`.
- **Itérer sur les images, pas sur les vidéos.** Une vidéo coûte en général des dizaines de fois plus qu'une image (un retour d'utilisateur mi-2026 indiquait environ 2 crédits l'image contre 72 le clip vidéo ; les tarifs changent, vérifie). Une image clé ratée détectée avant la vidéo est une économie directe.
- **Journal** : consigner chaque génération dans `studio/credits.md` (date, modèle, but, coût, fichier retenu ou rejeté).
- **Point d'arrêt obligatoire avant la première vidéo** : montrer les images clés retenues et le coût estimé des clips, attendre l'accord. Exception : l'utilisateur a explicitement demandé le mode autonome avec un plafond de crédits.

## 3. Commandes CLI utiles

Vérifie toujours les options avec `--help` : elles évoluent.

```bash
higgsfield account                                   # solde et transactions
higgsfield model list                                # catalogue à jour
higgsfield model --help                              # inspecter le schéma d'un modèle
higgsfield upload ./studio/assets/raw/produit.jpg    # envoyer une image de référence

# Image
higgsfield generate create nano_banana_2 \
  --prompt "<prompt>" --aspect_ratio 16:9 --resolution 2k --wait

# Vidéo depuis une image de départ
higgsfield generate create kling3_0 \
  --prompt "<mouvement>" --start-image ./studio/assets/keyframes/kf-01.png \
  --duration 5 --wait

# Suivi des travaux
higgsfield generate list --json
higgsfield generate get <job_id>
higgsfield generate wait <job_id>

# Recadrer une vidéo pour le mobile
higgsfield generate workflow reframe --video ./clip.mp4 --aspect-ratio 9:16 --resolution 720p --wait

# Photos produit de niveau marque (modes studio, lifestyle, bannière héros…)
higgsfield product-photoshoot --help
```

Le paramètre d'**image de fin** (pour relier deux images clés) dépend du modèle : lire le schéma du modèle vidéo choisi avant de construire la commande. Si le modèle n'accepte qu'une image de départ, générer chaque clip depuis son image clé et décrire l'état final dans le prompt.

Ajouter `--json` pour récupérer l'URL du résultat de façon fiable, puis la télécharger dans `studio/assets/`.

## 4. Choisir les modèles

Le catalogue change vite : confirme avec `higgsfield model list`. Repères au moment de la rédaction :

| Besoin | Point de départ |
|---|---|
| Produit, packaging, image avec texte lisible | `gpt_image_2` |
| Photo lifestyle ou éditoriale réaliste | `nano_banana_2` ou modèles Soul |
| Retouche fidèle d'une photo existante | `flux_kontext`, `nano_banana_2` avec image de référence |
| Détourage | `image_background_remover` |
| Logo, pictos, vectoriel | `recraft_v4_1` |
| Vidéo haut de gamme | `seedance_2_0`, `veo3_1`, `kling3_0` |
| Brouillon vidéo moins cher | `seedance_2_0_mini`, `kling3_0_turbo`, `veo3_1_lite` |
| Pub UGC / avatar + produit | Marketing Studio (`higgsfield marketing-studio --help`) |

## 5. Méthode des images clés

Une longue vidéo générée d'un bloc dérive : le produit change de forme, le décor glisse. La méthode fiable :

1. **Écrire le storyboard** dans `studio/storyboard.md` : 3 à 6 moments qui racontent quelque chose (situation → action → révélation → résultat), pas 5 jolies images interchangeables. Pour chaque moment : ce qu'on voit, le cadrage, le texte superposé prévu et où il se place (zone calme de l'image).
2. **Générer les images clés** avec la bible visuelle et la photo produit en référence. 2 à 4 variantes par moment.
3. **Revue visuelle** : ouvrir chaque image et appliquer la grille de la section 7. Régénérer ce qui échoue. C'est l'étape où la qualité se joue.
4. **Point d'arrêt budget** (section 2).
5. **Générer les clips** entre images clés consécutives (image de départ → image de fin quand le modèle le permet). Durée 4 à 8 s chacun.
6. **Variante mobile** : générer les images clés en 9:16 dès le départ si le mobile domine, sinon utiliser le workflow `reframe` ; le recadrage automatique d'une vidéo 16:9 donne souvent une image trop petite.
7. **Assembler** avec `scripts/video_to_frames.py` (plusieurs `--input` s'enchaînent dans l'ordre).

## 5 bis. Une image d'essai avant la série — et ce n'est pas négociable

**La règle.** Avant de lancer une série d'images dans un registre visuel qu'on
n'a jamais produit, on en génère **une seule**, on l'ouvre, et on la compare à
la référence. Ensuite seulement on lance le reste.

**Pourquoi elle existe.** Le 14 septembre 2026, neuf avatars ont été lancés d'un
coup pour une console. Ils sont sortis techniquement irréprochables — surfaces
vides, touches de clavier sans lettrage, mains correctes, aucun logo — et
**dans le mauvais registre** : des sculptures réalistes et graves là où la
référence montrait des figurines stylisées et joyeuses.

Le défaut n'était pas dans l'exécution, il était dans le cadrage. Une image
d'essai l'aurait montré pour 0,12 crédit ; neuf ont coûté huit fois plus pour
apprendre la même chose.

**Ce que l'essai vérifie, dans cet ordre :**

1. **Le registre** — est-ce la même *famille* que la référence ? Stylisé ou
   réaliste, joyeux ou grave, détouré ou en situation. C'est ce qui se rate le
   plus souvent, et c'est ce qu'aucune relecture de prompt ne rattrape.
2. **La proportion** — cadrage, place du sujet, marge.
3. **Les surfaces vides** — aucun faux lettrage, aucun logo. Décrire
   positivement la surface vide, jamais interdire.
4. **L'anatomie** — mains, doigts, visages.

**Le piège du plan gratuit.** Higgsfield n'accepte que **quatre travaux
simultanés** sur la formule gratuite. Une série de douze part en file, et une
correction de registre doit attendre que la file se vide. Raison de plus pour
que l'essai vienne en premier : il occupe un créneau, pas neuf.

**Quand on peut s'en passer** : jamais sur un registre neuf. Sur un registre
déjà validé dans le même projet, l'essai est inutile — la référence, c'est la
série précédente.

## 6. Formules de prompts

**Image clé**

```
<Sujet exact et fidèle : "le flacon ambré de 50 ml de la photo de référence, étiquette intacte">
<Moment du récit : ce qui se passe>
<Cadrage : plan, angle, focale, place du sujet, zone vide réservée au texte (ex. tiers gauche)>
<Décor et accessoires, cohérents avec la marque>
<Bible visuelle copiée telle quelle>
```

**Clip vidéo**

```
<Mouvement de caméra unique et lent : travelling avant, orbite de 30°, montée verticale>
<Mouvement du sujet : ce qui bouge et ce qui reste fixe>
<État final : à quoi ressemble la dernière image>
<Rythme : lent et continu, sans coupe>
<Contraintes : le produit garde sa forme et son étiquette ; pas de texte ; pas de nouvel objet>
<Bible visuelle>
```

Règles :
- Un seul mouvement de caméra par clip. Les combinaisons produisent des mouvements « ivres ».
- Pour le défilement, préférer des mouvements continus sans coupe ni flash : chaque image doit fonctionner comme arrêt sur image.
- Garder une zone calme (ciel, mur, fond flou) là où le texte sera superposé.

## 7. Fidélité produit et contrôle qualité

Grille de revue pour chaque image clé et pour les premières, milieu et dernière images de chaque clip :

- Le produit est-il identique à la référence (forme, proportions, couleur, étiquette, logo) ?
- Aucun texte inventé, aucun faux logo, aucun filigrane ?
- Mains, visages, reflets et ombres cohérents ?
- Palette et lumière conformes à la bible ?
- La zone réservée au texte est-elle réellement calme et lisible ?
- Cohérence avec les autres images (même décor, même lumière, même produit) ?

Une image qui échoue un seul critère sur le produit est rejetée, même si elle est belle.

## 8. Du clip au site

```bash
python3 scripts/video_to_frames.py \
  --input studio/assets/video/clip-01.mp4 --input studio/assets/video/clip-02.mp4 \
  --mobile-input studio/assets/video/mobile-01.mp4 --mobile-input studio/assets/video/mobile-02.mp4 \
  --out <projet>/public/frames --desktop-frames 150 --mobile-frames 90
```

Repères de réglage :
- **Nombre d'images** : environ 30 à 40 par écran de défilement desktop. Au-delà, le poids augmente sans gain visible.
- **Profil data léger** : `--mobile-frames 48 --mobile-width 540 --quality 65`.
- **Saccades** : si les clips sont en 24–30 i/s et que la séquence manque de fluidité, augmenter légèrement le nombre d'images ou allonger la longueur de défilement plutôt que d'interpoler à 60 i/s, qui double le poids.
- Toujours relancer `scripts/check_budget.py` après la construction.

## 9. Mode dégradé sans Higgsfield

Sans génération disponible, le site reste haut de gamme si :
- Les photos fournies sont traitées avec soin : recadrage fort, détourage, fonds unis de la palette, grands formats.
- Le moment mémorable passe par la typographie, une révélation en CSS/SVG ou une vidéo fournie par le client.
- Aucune banque d'images générique ne remplace le vrai produit.

Indiquer clairement à l'utilisateur ce que la génération aurait ajouté et le coût estimé, pour qu'il décide.
