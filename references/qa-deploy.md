# Revue qualité, déploiement et livraison

## 1. Boucle de revue (au moins deux tours)

```bash
npm run build
npm run preview &            # garder le serveur : les contrôles s'exécutent contre lui
python3 <skill>/scripts/preflight.py http://localhost:4173/<base>/ \
        --dist dist --facts studio/facts.json --market us --out studio/review
```

`preflight.py` enchaîne poids → chiffres → livraison → revue et **refuse de rendre
la main tant qu'un contrôle bloque**. Tant qu'il n'affiche pas « PRÊT À DÉPLOYER »,
on ne déploie pas : c'est la seule porte.

**L'URL passée doit être celle qui sert réellement le build, chemin de base
compris.** Servir `dist/` à la racine d'un serveur statique quand le site attend
`/mon-projet/` donne une page blanche — et une page blanche ne contient aucun
chiffre, donc aucun écart : le contrôle des chiffres rendait « OK » sur du vide.
Il refuse désormais toute page de moins de 200 caractères, mais l'erreur reste la
plus traître du lot. Utiliser `npm run preview`, jamais un serveur statique improvisé.

Puis **ouvrir les captures** (desktop et mobile, chaque profondeur de défilement, version légère) et juger comme un directeur artistique :

- Premier écran : promesse lisible, action visible, rien de cassé pendant le chargement.
- Chaque temps fort : texte lisible sur l'image du moment, bien placé, sans chevauchement avec le header.
- Mobile : pas de texte coupé, pas de débordement horizontal, boutons atteignables au pouce.
- Version légère : page complète et convaincante, pas une page dégradée.
- Cohérence : couleurs, polices et espacements conformes au plan.
- Chiffres : `check_facts.py` à « OK », et chaque graphique relu à l'œil contre sa légende (unité, total, proportions). Voir `facts.md`.

Corriger, reconstruire, relancer la revue. S'arrêter quand un nouveau tour ne trouve plus rien de significatif.

Si Playwright n'est pas disponible dans l'environnement, utiliser le MCP Playwright pour les mêmes captures, ou demander à l'utilisateur deux captures d'écran mobile.

## 2. Médias livrés : vérifier le fichier produit, jamais la source

```bash
python3 <skill>/scripts/check_media.py site/public/video/*.mp4 --out studio/review
```

Puis **ouvrir la dernière image extraite**. Une coupe se juge sur ce qui est servi :
chercher le point de coupe dans le fichier d'origine avec un positionnement rapide
(`ffmpeg -ss` placé avant `-i`) tombe sur l'image-clé la plus proche, pas sur
l'image demandée. Une vidéo coupée d'après cette mesure garde une seconde de trop,
et personne ne s'en aperçoit avant que le client ne regarde la fin.

Vérifier aussi ce que la vidéo dit. Un contenu repris des réseaux sociaux se termine
souvent par un appel à suivre un compte : sur la page du client, cette fin envoie
les visiteurs ailleurs. La couper.

## 3. Contrôles complémentaires

- **Lighthouse** (si Chrome disponible) : `npx lighthouse http://localhost:4173 --preset=desktop --only-categories=performance,accessibility,seo,best-practices` puis sans preset pour le mobile. Viser ≥ 90 en accessibilité, SEO et bonnes pratiques ; en performance mobile, ≥ 80 sur une page cinématique, ≥ 90 sinon.
- **Textes restants** : `grep -rn "\[" src/content.ts` doit être vide avant déploiement (sauf emplacements volontaires signalés).
- **Liens** : chaque bouton mène au bon endroit (WhatsApp avec message pré-rempli, produit, formulaire).
- **Clavier** : tabulation dans l'ordre logique, focus visible, FAQ ouvrable au clavier.
- **Mouvement réduit** : activer l'émulation `prefers-reduced-motion` et vérifier la version légère.

## 3b. Les e-mails transactionnels se vérifient sur le message reçu

Un site qui envoie des e-mails livre deux produits, pas un. Le second ne passe
par aucun navigateur, aucune capture, aucun contrôle : **il n'existe que dans
une boîte de réception**. C'est l'angle mort le plus courant.

**Déclencher chaque chemin pour de vrai, puis lire le message reçu.** Pas le
gabarit dans le code : le message, avec ses en-têtes, dans le journal du
fournisseur d'envoi ou dans la boîte.

**La règle qui a coûté le plus cher** :

> Un e-mail ne donne jamais une instruction que ses propres en-têtes ne
> permettent pas.

« Répondez directement » exige un `Reply-To`. Sans lui, répondre renvoie
l'équipe à sa propre boîte, et personne ne s'en aperçoit : le message part, il
ne revient pas en erreur, il n'arrive nulle part. Le 12 septembre 2026, un
prospect qui laissait un numéro WhatsApp sans e-mail déclenchait exactement
cela.

**Ce qu'on vérifie sur chaque message reçu :**

- l'expéditeur est le domaine du client, pas le bac à sable du fournisseur ;
- `Reply-To` pointe sur le prospect, et l'instruction du pied de page
  correspond au canal réellement disponible ;
- chaque moyen de contact est **actionnable en un geste** : un numéro devient
  un lien `wa.me`, une adresse un `mailto:`. Ce message se lit sur un
  téléphone, et un numéro à recopier est un délai de plus ;
- les chiffres viennent du registre de faits, comme sur la page ;
- le rendu tient sans CSS moderne : styles en ligne, aucune feuille externe.

**Énumérer les chemins, pas seulement le principal.** Formulaire complet,
conversation avec e-mail, conversation avec téléphone seul, et le cas où le
visiteur ne donne rien. Chacun produit un message différent, ou pas de message
du tout — et « pas de message » est une décision à assumer, pas un oubli.

**Ce qui reste à construire** : aucun script ne contrôle encore ces messages.
C'est une lacune connue du skill, à combler le jour où une création envoie plus
de deux e-mails. En attendant, c'est une lecture, et elle est obligatoire.

## 4. Déploiement

| Cible | Commande | Remarque |
|---|---|---|
| Vercel | `npx vercel` puis `npx vercel --prod` | Compte requis ; domaine personnalisé dans le tableau de bord |
| Cloudflare Pages | `npx wrangler pages deploy dist` | Bon réseau de diffusion mondial, y compris en Afrique |
| Netlify | `npx netlify deploy --dir=dist --prod` | Formulaires simples intégrés |
| Railway / autre via GitHub | Pousser le dépôt, relier une fois | Redéploiement à chaque `git push` |
| Higgsfield | `higgsfield website deploy <website_id>` | Voir `build.md` §4 |
| GitHub Pages | Copier `dist/` dans la branche `gh-pages` et pousser | Voir l'encadré ci-dessous : des fichiers de service vivent dans cette branche |

**GitHub Pages : tout ce que la branche doit garder vient du build.** Un déploiement vide la branche et y recopie `dist/`. Les fichiers qui n'y sont pas disparaissent en silence, et ce sont justement les fichiers de service : `CNAME` (le domaine personnalisé, sans lui le site retombe sur l'adresse `github.io`) et `.nojekyll` (sans lui, Pages passe le build à Jekyll et ignore tout chemin commençant par un tiret bas). Ils doivent vivre dans `public/`, donc être émis par chaque build — jamais être ajoutés à la main dans la branche, où le déploiement suivant les emportera.

**Un média remplacé change de nom.** Le JavaScript et le CSS reçoivent une empreinte
au build, pas les fichiers de `public/`. Republier une vidéo ou une image sous le
même nom laisse les téléphones servir l'ancienne version depuis leur cache — le
client voit la version corrigée nulle part et croit que rien n'a bougé. Passer de
`clip.mp4` à `clip-2.mp4` règle la question définitivement.

### La consigne donnée au client est un livrable, et elle a ses propres défauts

Un site professionnel demande presque toujours des étapes que seul le client
peut faire : poser des enregistrements DNS, créer un compte, coller une clé.
Ces consignes ne passent aucun contrôle — le défaut ne se produit pas dans le
code, il se produit **entre la consigne et la main du client**.

**Ne jamais présenter un réglage sous forme de tableau dont les en-têtes
reprennent les étiquettes du formulaire visé.** Le 12 septembre 2026, un réglage
Supabase donné ainsi :

| Nom | Valeur |
|---|---|
| `QUOTE_FROM` | `Ma Boutique <onboarding@resend.dev>` |

a produit, quatre-vingt-dix secondes plus tard, un secret réellement nommé
`VALEUR` dans le projet. Le formulaire a deux champs étiquetés « Nom » et
« Valeur » : l'en-tête a été saisi comme s'il était le contenu. La faute est
celle de la mise en forme, pas celle du client.

**La forme sûre est une ligne par champ, avec l'étiquette exacte de l'écran :**

> Dans le champ **Nom** : `QUOTE_FROM`
> Dans le champ **Valeur** : `Ma Boutique <onboarding@resend.dev>`

Un tableau reste bon quand il énumère **plusieurs** entrées de même nature —
les quatre lignes DNS d'un domaine, par exemple : là, chaque ligne est un objet
distinct et l'en-tête ne peut pas être confondu avec un contenu.

**Toute étape confiée se termine par une vérification, et la plupart ne peuvent
pas être vérifiées par un script.** Le DNS, on le relit aux serveurs faisant
autorité. Une clé posée dans une interface, non : aucune API ne la relit. Il
faut alors **demander la capture de l'écran après l'action** et lire ce qui s'y
trouve réellement, y compris les lignes dont on n'a pas parlé. C'est exactement
ce qui a manqué ce jour-là : la ligne parasite est restée douze heures avant
d'apparaître, par hasard, sur une capture envoyée pour une autre raison.

**Ce qu'on note à chaque fois** : une étape confiée au client est un point
d'abandon et une source de défauts. Elle s'inscrit comme un connecteur à
construire, pour que la fois suivante elle n'existe plus.

Ne jamais déployer en production sans accord explicite de l'utilisateur ; une prévisualisation peut être proposée d'office.

Après déploiement : relancer `preflight.py` sur l'URL en ligne. Les chemins, les
en-têtes de cache et surtout les URL absolues (image de partage, adresse canonique)
diffèrent du local — et c'est en ligne que le lien partagé sera testé.

## 5. Après la livraison : la porte reste en place

**Un site vérifié aujourd'hui ne l'est pas dans trois mois.** Une clé expire, un
palier gratuit sature, un enregistrement DNS est modifié, un catalogue externe
ferme. Sans surveillance, **c'est le client qui l'apprend** — et pour une
livraison vendue comme vérifiée, c'est le pire échec possible : on a promis
exactement ce qu'on a laissé se défaire.

Déposer `assets/workflows/verification-continue.yml` dans
`.github/workflows/` du dépôt du client. Une seule valeur à changer : `SITE_URL`.

Ce qu'il fait, et pourquoi c'est fait ainsi :

- il tourne **contre le site en ligne**, pas contre le build. C'est la règle
  d'or : on vérifie ce qui est servi ;
- il **ouvre une issue** quand un bloquant apparaît, et la **referme seul** quand
  il disparaît. Pas un e-mail de plus que personne ne lit ;
- `issues: write` et rien d'autre. Il ne peut pas toucher au code.

**Ce que ça change commercialement.** Une vérification à la livraison se paie une
fois. Une vérification qui reste vraie se paie tous les mois. C'est le même
script : seule la fréquence change, et avec elle le modèle.

## 6. Livraison

Remettre à l'utilisateur :

1. **L'URL** (prévisualisation ou production) et une phrase sur ce qui rend la page distinctive.
2. **Le code source** (dossier ou dépôt) et comment le relancer.
3. **`studio/`** : brief, storyboard, bible visuelle, images clés et clips retenus, journal de crédits.
4. **Ce qui reste à fournir** : témoignages réels, mentions légales, visuels manquants, emplacements signalés.
5. **Tableau des chiffres** : chaque chiffre affiché, où il apparaît, sa source (depuis `studio/facts.json`).
6. **Résultats de la revue** : budgets, contrôle des chiffres, scores Lighthouse si mesurés, points connus.

Format du message final : court, orienté action. Pas de liste de tout ce qui a été fait ; l'essentiel est l'URL, les éléments à compléter et le coût en crédits.
