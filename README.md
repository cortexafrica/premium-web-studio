# premium-web-studio

Un skill [Claude Code](https://claude.com/claude-code) qui transforme un lien,
une photo produit, un logo, une fiche Shopify ou une simple idée en un site
vitrine ou une landing page de niveau agence — avec direction artistique,
production visuelle, séquences cinématiques pilotées par le défilement, revue
automatisée et porte de déploiement.

Le skill ne se contente pas de décrire une méthode : il embarque **dix scripts
de contrôle** qui refusent le déploiement tant qu'un défaut mesurable subsiste.

## Installation

```bash
git clone https://github.com/cortexafrica/premium-web-studio.git \
  ~/.claude/skills/premium-web-studio
```

Le skill est alors disponible dans Claude Code. Il se déclenche tout seul
lorsque la demande ressemble à « fais-moi un site », ou à l'appel : `/premium-web-studio <lien, image ou description>`

Pour l'installer sur un seul projet plutôt que sur tout le compte, cloner dans
`.claude/skills/` à la racine du projet.

## Dépendances

Tout est optionnel — chaque script dégrade proprement s'il manque son outil.

| Outil | Sert à |
|---|---|
| Python 3 | tous les scripts |
| Pillow | extraction de palette |
| ffmpeg (avec libwebp) | séquences d'images depuis une vidéo |
| Playwright + Chromium | revue visuelle, contrôle des faits, contrôle de sortie |
| Higgsfield (MCP, CLI ou skills) | génération d'images et de vidéos |

## Ce qu'il y a dans la boîte

- **[`SKILL.md`](SKILL.md)** — la consigne : règles d'or, espace de travail,
  déroulé en sept étapes du brief au déploiement.
- **[`references/`](references/)** — neuf dossiers de fond : intake et droits,
  direction artistique, rédaction, pipeline Higgsfield, construction, registre
  des chiffres, assistant de conversation, sécurité, recette et déploiement.
- **[`scripts/`](scripts/)** — les contrôles. Poids du build, chiffres non
  sourcés, police réellement appliquée, médias livrés, revue desktop / mobile /
  Safari, secrets dans le dépôt **et son historique**, SPF / DMARC / CAA /
  DNSSEC. `preflight.py` les enchaîne et bloque la livraison au premier échec.
- **[`assets/cinematic-template/`](assets/cinematic-template/)** — un point de
  départ Vite + React + TypeScript avec séquence au défilement et défilement
  lissé.
- **[`tests/`](tests/)** — chaque contrôle sensible tient ses cas connus-faux.
  Un contrôle sans cas connu-faux peut passer au vert simplement parce qu'il ne
  regarde pas.
- **[`demo/police/`](demo/police/)** — la démonstration d'un défaut réel : une
  police servie sans son sous-ensemble latin, qui se télécharge sans erreur et
  ne produit aucun message nulle part.

## Lancer les tests

```bash
python tests/test_etat_divulgue.py
python tests/test_fiction_declaree.py
```

## Un mot sur le « site à 10 000 $ »

C'est une exigence de qualité interne, pas une promesse commerciale. Le skill
interdit explicitement d'employer la formule dans les textes livrés au client
final — au même titre qu'il interdit d'inventer un témoignage, un chiffre ou un
label.

## Licence

MIT — voir [`LICENSE`](LICENSE). Les polices de `demo/police/` restent sous SIL
Open Font License 1.1 ([`demo/police/OFL.txt`](demo/police/OFL.txt)).
