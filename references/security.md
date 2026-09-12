# Sécurité

## La promesse qu'on ne fait pas

**Aucun site n'est impossible à pirater.** Ni celui-ci, ni ceux des banques.
Un outil qui promettrait l'inviolabilité serait dangereux pour une raison
simple : on cesse de surveiller ce qu'on croit invulnérable.

Ce qu'on fait à la place, et qui marche :

1. **Réduire ce qu'il y a à voler.** Pas de clé dans le navigateur, pas de base
   de données quand un fichier suffit, pas de compte utilisateur sur un site
   vitrine.
2. **Rendre l'effort disproportionné.** Les intrusions réelles visent ce qui
   est facile. Un site correct n'intéresse personne face à dix mille sites
   laissés ouverts.
3. **Trouver avant livraison.** `check_security.py` cherche les erreurs
   connues sur ce type d'architecture, à chaque livraison.
4. **Borner les dégâts.** Une clé qui fuit doit pouvoir être révoquée en une
   minute. Un formulaire abusé doit s'arrêter tout seul.

Et dire honnêtement ce qui reste ouvert. Un rapport qui ne liste que des
succès n'a pas été lu jusqu'au bout.

## Ce qui casse vraiment ces sites

Par fréquence réelle, pas par spectacle :

| Ce qui arrive | Ce qui l'empêche |
|---|---|
| Une clé d'API dans le dépôt ou le build | `check_security.py`, à chaque livraison |
| Un compte repris (registrar, hébergeur, e-mail) | double authentification partout, sans exception |
| Une fonction serveur appelable par n'importe qui | contrôle d'origine **exigé**, plafonds persistants |
| Un domaine détourné | DNSSEC, CAA, verrou du registrar |
| Une dépendance compromise | versions figées, `npm audit` avant livraison |

Les trois premières lignes causent plus d'intrusions que toutes les techniques
dont on parle dans la presse.

## Les clés : la seule urgence absolue

Un site statique n'a pas de serveur : **toute clé placée dans le code est
lisible par chaque visiteur**. C'est pourquoi les appels payants passent par
une fonction serveur qui, elle, détient la clé.

Trois règles :

- **Jamais dans le dépôt**, ni dans un fichier, ni dans un commentaire, ni dans
  un fichier d'exemple. Les dépôts publics sont moissonnés en continu par des
  robots : une clé y vit quelques minutes avant d'être utilisée.
- **Jamais dans la conversation** avec un assistant. Une clé collée dans un
  chat est une clé à révoquer.
- **L'historique compte autant que le présent.** Retirer une clé d'un fichier
  ne l'efface pas du dépôt : elle reste téléchargeable. La seule réponse qui
  ferme la porte est **la révocation chez le fournisseur**.

## Les fonctions serveur : le piège du contrôle d'origine

C'est l'erreur la plus fréquente, et la plus discrète :

```ts
if (origin && !ALLOWED_ORIGINS.includes(origin)) return refus();   // TROUÉ
```

Une requête **sans** en-tête `Origin` passe : `origin` vaut la chaîne vide, la
condition est fausse, et le contrôle ne s'applique pas. Or un navigateur envoie
toujours cet en-tête sur une requête croisée — **seul un client qui n'en est
pas un peut l'omettre**. Le code ci-dessus laisse donc entrer exactement ce
qu'il croyait bloquer.

```ts
if (!ALLOWED_ORIGINS.includes(origin)) return refus();             // correct
```

Ce n'est pas infaillible : un en-tête se forge. Mais cela fait passer l'abus de
trivial à délibéré, et c'est tout ce qu'un contrôle d'origine peut prétendre.

**Un plafond en mémoire n'est pas un plafond.** `const hits = new Map()` sur une
fonction sans état : chaque instance a le sien, un démarrage à froid le remet à
zéro. Le plafond annoncé n'existe pas. Pour qu'il tienne, il faut un compteur
persistant en base.

## Quand une fonction peut envoyer un e-mail

C'est le cas le plus dangereux, parce qu'il coûte plus que de l'argent : il
brûle la réputation d'envoi du domaine, et celle-ci met des mois à revenir.

La question à se poser : **qui choisit le destinataire ?**

- Destinataire **fixe**, côté serveur : le risque est borné à du bruit.
- Destinataire **fourni par l'appelant** : c'est un relais. Quelqu'un peut faire
  partir un message estampillé de la marque vers l'adresse de son choix.

Quand le second cas est nécessaire — un accusé de réception au prospect, par
exemple — il faut l'encadrer :

- en-tête d'origine exigé ;
- plafond **propre** à cet envoi, plus sévère que les autres, et **global**, pas
  seulement par IP : un plafond par IP ne protège de rien quand l'attaquant en
  change ;
- piège à robots qui court-circuite **avant** tout effet de bord ;
- et l'accepter comme un compromis conscient, écrit dans le code, pas comme un
  oubli.

## L'assistant de conversation

Deux risques propres, qui n'existent pas sur un site sans IA :

- **L'injection par la consigne.** Un visiteur écrit « oublie tes instructions ».
  La parade tient en trois points : une règle dure qui l'interdit, une base de
  faits d'où viennent toutes les affirmations, et un périmètre énuméré. Voir
  `assistant.md`.
- **La consommation du crédit.** La fonction appelle un modèle payant. Sans
  contrôle d'origine ni plafond, un script vide le compte en une nuit.

Et une règle qui vaut pour toute réponse d'API : **ne jamais relayer le corps
d'erreur du fournisseur** au visiteur. Il contient parfois des détails de compte.

## Les en-têtes, et la limite de l'hébergement statique

GitHub Pages **n'envoie aucun en-tête de sécurité et ne permet pas d'en
ajouter**. Ce n'est pas un oubli à corriger, c'est une propriété de la
plateforme. Le dire au client plutôt que de laisser croire le contraire.

Quand ces en-têtes comptent — un site qui manipule des données, pas une vitrine
— la réponse est de placer un intermédiaire devant : Cloudflare en offre gratuite
donne le contrôle complet des en-têtes, le HSTS, et un filtrage du trafic.
C'est un changement d'architecture, pas un réglage : à proposer, pas à décider
seul.

## Le domaine : ce qui annule tout le reste

Un détournement de domaine bat chaque protection mise en place : l'attaquant
sert son propre site à votre adresse, avec un certificat valide.

- **Verrou du registrar** activé, et double authentification sur ce compte.
- **DNSSEC** : signe les réponses DNS, empêche qu'on en fabrique une.
- **CAA** : dit quelle autorité a le droit d'émettre un certificat pour le
  domaine. Sans lui, n'importe laquelle peut.
- **SPF, DKIM, DMARC** dès que le domaine envoie du courrier. DMARC est celui
  qu'on oublie, et c'est lui qui rend les deux autres utiles : il dit aux
  serveurs destinataires quoi faire d'un message usurpé.

## Ce qu'aucun script ne verra

À dire au client, à chaque livraison :

- un mot de passe réutilisé entre le registrar et une boutique en ligne ;
- la double authentification absente sur un des comptes ;
- un accès laissé actif à un ancien prestataire ;
- une clé partagée par messagerie et jamais révoquée.

**Ces quatre-là causent plus d'intrusions que toutes les failles techniques
réunies.** Un rapport de sécurité qui ne les mentionne pas donne une fausse
assurance, et la fausse assurance est elle-même une vulnérabilité.

## Le contrôle

```bash
python3 scripts/check_security.py <url en ligne> --dist dist --repo . \
        --functions <url1>,<url2> --out studio/review
```

Il fait partie de `preflight.py` et bloque comme les autres. Ce qu'il trouve,
on le corrige ; ce qu'on choisit de ne pas corriger, on l'écrit dans la
livraison avec la raison.
