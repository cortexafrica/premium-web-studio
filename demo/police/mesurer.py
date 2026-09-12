#!/usr/bin/env python3
"""Mesure les deux sous-ensembles et reproduit le constat du 12 septembre 2026.

Le fichier fautif s'est telecharge sans erreur, s'est preche sans erreur, et
n'a produit aucun message nulle part. Le seul symptome visible etait que la
lettre A sortait dans une autre graisse que le reste du texte.

    python3 mesurer.py
"""
import sys

try:
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("fontTools manquant : pip install fonttools brotli")

FICHIERS = [
    ("archivo-VIETNAMIEN-le-fautif.woff2", "ce qui etait servi"),
    ("archivo-LATIN-le-correct.woff2", "ce qu'il fallait servir"),
]

ASCII = [chr(c) for c in range(0x20, 0x7F)]

print(f"{'fichier':42} {'glyphes':>8} {'ASCII couvert':>14}  lettres latines\n")
for nom, role in FICHIERS:
    f = TTFont(nom)
    cmap = f.getBestCmap()
    couverts = [c for c in ASCII if ord(c) in cmap]
    lettres = [c for c in couverts if c.isalpha()]
    apercu = "".join(lettres[:12]) + ("..." if len(lettres) > 12 else "")
    print(f"{nom:42} {len(cmap):8} {len(couverts):>7} / {len(ASCII):<4}  {apercu or '(aucune)'}")
    print(f"{'  ' + role:42}")

print("\nLe fichier vietnamien couvre UNE seule lettre latine : le A.")
print("Toute la page tombait donc dans la police systeme du visiteur, et le A")
print("seul sortait en Archivo. Sur un poste Windows le repli est Segoe UI :")
print("assez plausible pour qu'on ne voie rien.")
print("\nC'est check_release.py qui le trouve, en mesurant chaque caractere de")
print("la page avec deux polices temoins. Un temoin unique produisait des faux")
print("positifs : 'a', 'e' et '7' etaient signales a tort.")
