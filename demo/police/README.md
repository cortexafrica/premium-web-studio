# Le sous-ensemble vietnamien

Le défaut trouvé sur le site Ma Boutique, le 12 septembre 2026. C'est la
démonstration à montrer en premier : elle se comprend sans explication, et
personne d'autre ne la voit.

## Ce qui s'est passé

Le fichier servi sous le nom `archivo-latin-ext.woff2` était le sous-ensemble
**vietnamien** d'Archivo. Il contient 115 glyphes et **une seule lettre latine :
le A**.

Toute la page tombait donc dans la police système du visiteur. Seul le A sortait
en Archivo — d'où des « A » d'une autre graisse au milieu des mots, visibles sur
`Amazon FBA` et sur `A minute with our team`.

## La mesure

```
$ python3 mesurer.py

fichier                                     glyphes  ASCII couvert  lettres latines
archivo-VIETNAMIEN-le-fautif.woff2              115       2 / 95    A
archivo-LATIN-le-correct.woff2                  230      95 / 95    ABCDEFGHIJKL...
```

Et le verdict du contrôle sur la page rendue :

```
❌ La police « Archivo » ne couvre que 1 des 77 caractères de la page :
   le texte s'affiche en police système et l'identité typographique n'existe pas.
```

Les deux chiffres mesurent des choses différentes, et les deux sont exacts :
**2 sur 95** compte l'ASCII dans le fichier ; **1 sur 77** compte les caractères
réellement présents sur la page, en écartant ceux dont les deux polices témoins
ne se distinguent pas.

## Avant et après

`1-avant-police-vietnamienne.jpg` et `2-apres-police-latine.jpg` : la même page,
le même serveur, seul le fichier de police change.

Regarde les retours à la ligne. **« Open a dollar store. » tient sur une ligne
avec la vraie police, sur deux sans elle.** Le héros perd une ligne entière, le
paragraphe en gagne une, toute la composition se décale.

**Et pourtant, vue seule, la version cassée paraît normale.** C'est là toute la
difficulté : sur un poste Windows le repli est Segoe UI, une police
professionnelle et plausible. Rien ne signale une erreur. C'est exactement
pourquoi ce site est parti en production avec le défaut.

## Pourquoi rien ne l'a signalé

- le fichier se **télécharge** sans erreur : 200, 13 240 octets ;
- il se **précharge** sans erreur ;
- aucun avertissement dans la console ;
- la page **semble** bien composée.

Un contrôle qui lit le code ne voit rien : la déclaration `@font-face` est
correcte, le chemin est bon, le fichier existe. Le défaut n'est visible que
**dans le rendu**.

## Comment le contrôle le trouve

`check_release.py` mesure, caractère par caractère, la largeur du texte composé
avec la famille déclarée puis avec **deux polices témoins** de métriques
différentes. Si le caractère est couvert, la famille l'emporte et les deux
largeurs coïncident. S'il manque, chaque pile suit son propre témoin et les
largeurs divergent.

**Deux témoins, pas un.** Avec un seul, un caractère bien couvert dont la largeur
coïncide par hasard avec celle du témoin passe pour un repli : « a », « e » et
« 7 » ont été signalés à tort avant cette correction. Un contrôle qui crie au
loup cesse d'être lu.

## Ce que la démonstration prouve

Le site avait été relu, validé et publié. Ce n'est pas un défaut d'inattention :
**c'est un défaut qu'un œil humain ne peut pas voir.**

Il n'y a que deux façons de l'attraper : mesurer le rendu, ou ne jamais
l'attraper.
