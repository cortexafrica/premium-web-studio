#!/usr/bin/env python3
"""Cas connu-faux : la divulgation d'état de configuration en GET.

Un contrôle sans cas connu-faux ne prouve rien — il peut passer au vert parce
qu'il ne regarde pas. Ce fichier tient le sien.

Le cas 1 est un défaut réel : le corps exact que la fonction « ask » du site
Ma Boutique renvoyait à n'importe qui en GET, le 12 septembre 2026. Elle ne
livrait aucune clé, mais elle confirmait qu'il y en avait une et qu'elle était
en place — le premier renseignement que cherche quelqu'un qui sonde un service.

Les cas négatifs comptent autant : un contrôle qui crie sur tout se fait
désactiver, et un contrôle désactivé ne protège plus rien.

    python3 tests/test_etat_divulgue.py
"""
import importlib.util
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):      # Windows sert du cp1252 par défaut
    sys.stdout.reconfigure(encoding="utf-8")
else:                                        # Python < 3.7
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Le chemin se déduit de l'emplacement du test : un outil vendu ne connaît pas
# l'arborescence de celui qui l'exécute.
CIBLE = Path(__file__).resolve().parent.parent / "scripts" / "check_security.py"

spec = importlib.util.spec_from_file_location("check_security", CIBLE)
cs = importlib.util.module_from_spec(spec)
sys.modules["check_security"] = cs
spec.loader.exec_module(cs)

CAS = [
    # (corps servi, doit-il être signalé, ce qu'on éprouve)
    (b'{"keyDetected":true}', True, "le défaut réel du 12 septembre 2026"),
    (b'{"configured":false}', True, "l'aveu inverse : une clé manquante se dit aussi"),
    (b'{"version":"1.4.2"}', True, "une version sert à chercher la faille connue"),
    (b'{"debug":1}', True, "un mode debug laissé ouvert"),
    (b'{"error":"Method not allowed"}', False, "le refus attendu après correction"),
    (b'{"answer":"Nous sommes a Yiwu."}', False, "une réponse métier normale"),
    (b"", False, "un corps vide"),
    (b"<html>bonjour</html>", False, "une page HTML, pas du JSON"),
    (b"[1,2,3]", False, "un tableau JSON, pas un objet"),
]


def main():
    echecs = 0

    for corps, attendu, pourquoi in CAS:
        trouves = cs.etat_divulgue(corps)
        obtenu = bool(trouves)
        if obtenu != attendu:
            echecs += 1
        marque = "ok   " if obtenu == attendu else "ÉCHEC"
        detail = f"  → {trouves}" if trouves else ""
        print(f"{marque} {corps[:38]!r:42} {pourquoi}{detail}")

    # Un rapport est un fichier : il se partage et il se commit. Il ne doit
    # jamais devenir l'endroit où une valeur sensible finit par être écrite.
    secret = b'{"apiKey":"sk-abcdef0123456789abcdef0123456789"}'
    trouves = cs.etat_divulgue(secret)
    fuite = any("sk-abcdef" in str(valeur) for _, valeur in trouves)
    echecs += int(fuite)
    print(f"{'ÉCHEC' if fuite else 'ok   '} la valeur sensible n'est pas recopiée "
          f"dans le rapport  → {trouves}")

    total = len(CAS) + 1
    print(f"\n{total - echecs}/{total} cas conformes")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
