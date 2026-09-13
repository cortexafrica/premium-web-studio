# -*- coding: utf-8 -*-
"""Cas connu-faux du contrôle « fiction affichée sans mention de démonstration ».

Écrit le 13 septembre 2026, en même temps que le contrôle lui-même.

Pourquoi ce contrôle existe : la création DESTINY est une marque de vêtements
inventée, avec de vraies photographies, des prix et une date de sortie. Une
page pareille sera prise pour une vraie boutique. Quelqu'un peut y laisser son
adresse et attendre une livraison qui n'arrivera jamais. Le tort est réel même
sans transaction.

Le registre `facts.json` est l'endroit où la fiction se DÉCLARE — chaque valeur
porte `"type": "fiction"`. S'il la déclare et que la page ne dit rien, le
registre sert à cacher la fiction au lieu de l'avouer : exactement l'inverse de
son rôle. D'où ce contrôle.

Un contrôle sans cas connu-faux ne prouve rien : on vérifie les DEUX sens, ce
qu'il attrape et ce sur quoi il se tait.

    python tests/test_fiction_declaree.py
"""
import json
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

from check_facts import AVEUX, faits_fictifs  # noqa: E402


def registre(faits):
    """Écrit un registre temporaire et renvoie son chemin."""
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"facts": faits}, f, ensure_ascii=False)
    f.close()
    return f.name


def declaree(texte):
    """La règle appliquée par check_facts sur le texte rendu de la page."""
    return any(mot in texte.lower() for mot in AVEUX)


# --- Ce que le registre doit signaler ---------------------------------------
CAS_REGISTRE = [
    ("un fait marqué fiction est signalé",
     [{"id": "prix", "value": 168, "type": "fiction"}], ["prix"]),

    ("un fait réel ne l'est pas",
     [{"id": "capital", "value": 1000, "type": "verified", "source": "statuts"}], []),

    ("un fait sans type ne l'est pas — on ne présume pas la fiction",
     [{"id": "delai", "value": 14}], []),

    ("la casse ne doit pas permettre d'y échapper",
     [{"id": "a", "value": 1, "type": "Fiction"},
      {"id": "b", "value": 2, "type": "FICTION"}], ["a", "b"]),

    ("un registre mixte ne signale que la part inventée",
     [{"id": "vrai", "value": 3, "type": "verified"},
      {"id": "faux", "value": 9, "type": "fiction"}], ["faux"]),

    ("un registre vide ne déclenche rien",
     [], []),
]

# --- Ce que le texte de la page doit valoir ---------------------------------
CAS_TEXTE = [
    ("le bandeau anglais livré compte",
     "Demo — fictional brand, nothing is for sale. Collection One.", True),

    ("une mention française compte aussi",
     "Ceci est une démonstration : la marque est fictive.", True),

    ("« nothing is for sale » seul suffit",
     "Made in Los Angeles. Nothing is for sale on this page.", True),

    ("une page de marque crédible sans mention ne passe pas",
     "DESTINY. Collection One, out September 20. Cut and sewn in Los Angeles. "
     "Star Wide Leg Denim $168. Join the list.", False),

    # LIMITE CONNUE, inscrite ici pour qu'elle ne se découvre pas en production.
    # La recherche se fait par sous-chaîne : « Democratic » contient « demo »,
    # donc une page qui emploie ce mot est comptée comme déclarée alors qu'elle
    # n'avertit personne.
    #
    # On l'accepte, et voici pourquoi : le contrôle protège le visiteur d'une
    # page fictive qui se ferait passer pour vraie. Se tromper dans ce sens
    # laisse passer une page à corriger à la main ; se tromper dans l'autre —
    # exiger un mot exact — bloquerait des pages honnêtes rédigées autrement,
    # et un contrôle qui crie à tort finit désactivé. La relecture humaine
    # reste la dernière ligne, et elle est prévue au déroulé du skill.
    ("faux positif assumé : « Democratic » contient « demo »",
     "Democratic design, made in Denmark. Demolition denim.", True),
]


def executer():
    echecs = []

    for nom, faits, attendu in CAS_REGISTRE:
        chemin = registre(faits)
        try:
            obtenu = faits_fictifs(chemin)
        finally:
            Path(chemin).unlink(missing_ok=True)
        if sorted(obtenu) != sorted(attendu):
            echecs.append(f"registre — {nom} : attendu {attendu}, obtenu {obtenu}")

    for nom, texte, attendu in CAS_TEXTE:
        obtenu = declaree(texte)
        if obtenu != attendu:
            echecs.append(f"texte — {nom} : attendu {attendu}, obtenu {obtenu}")

    total = len(CAS_REGISTRE) + len(CAS_TEXTE)
    for e in echecs:
        print("ÉCHEC :", e)
    print(f"{total - len(echecs)}/{total} cas passés.")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(executer())
