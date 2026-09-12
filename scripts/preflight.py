#!/usr/bin/env python3
"""La seule porte de sortie avant un déploiement.

Enchaîne les quatre contrôles dans l'ordre où ils coûtent le moins cher à
corriger, et s'arrête sur le premier bloquant :

  1. check_budget.py   — le poids du build
  2. check_facts.py    — chaque chiffre affiché vient du registre
  3. check_release.py  — favicon, partage, mentions, 404, marché, contradictions
  4. review_site.py    — captures desktop, mobile et Safari, erreurs console

Tant que ce script n'a pas rendu « PRÊT À DÉPLOYER », on ne déploie pas. C'est
tout l'intérêt : sans porte, rien n'empêche de publier un site défectueux.

Usage :
  python3 preflight.py http://localhost:4173/base/ --dist site/dist --market us
  python3 preflight.py <url> --dist site/dist --facts studio/facts.json --out studio/review

Code de sortie 1 dès qu'une étape échoue.
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Une console Windows repond souvent en cp1252 : le premier caractere non
# latin-1 affiche interrompt le script et le controle ne rend aucun verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent


def run(label, command, blocking=True):
    print(f"\n{'=' * 68}\n{label}\n{'=' * 68}", flush=True)
    result = subprocess.run([sys.executable, *command])
    ok = result.returncode == 0
    if not ok and blocking:
        print(f"\n⛔ {label} : échec. On ne déploie pas.", flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="URL du site servi depuis le build (npm run preview, chemin de base compris)")
    ap.add_argument("--dist", default="dist", help="Dossier du build")
    ap.add_argument("--facts", default="studio/facts.json")
    ap.add_argument("--market", default="", help="Marché visé, ex. us")
    ap.add_argument("--out", default="studio/review")
    ap.add_argument("--claims", help="JSON de contradictions propres au projet")
    ap.add_argument("--live", help="URL du site EN LIGNE, pour le contrôle de sécurité complet")
    ap.add_argument("--repo", default=".", help="Racine du dépôt, pour l'historique git")
    ap.add_argument("--functions", default="",
                    help="URLs des fonctions serveur, séparées par des virgules")
    ap.add_argument("--skip-review", action="store_true", help="Saute la revue visuelle (la plus lente)")
    args = ap.parse_args()

    steps = []

    steps.append(("Poids du build", [str(HERE / "check_budget.py"), args.dist]))

    steps.append(("Chiffres affichés", [
        str(HERE / "check_facts.py"), args.url,
        "--facts", args.facts,
        "--out", str(Path(args.out) / "facts-report.json"),
    ]))

    release = [str(HERE / "check_release.py"), args.url,
               "--dist", args.dist,
               "--out", str(Path(args.out) / "release-report.json")]
    if args.market:
        release += ["--market", args.market]
    if args.claims:
        release += ["--claims", args.claims]
    steps.append(("Livraison", release))

    # La securite avant la revue visuelle : une cle qui fuit ne se rattrape pas
    # en corrigeant une capture. Sans --live on reste hors ligne, ce qui couvre
    # deja le plus important : les secrets dans le build et dans l'historique.
    secu = [str(HERE / "check_security.py"), args.live or args.url,
            "--dist", args.dist, "--repo", args.repo, "--out", args.out]
    if args.live:
        if args.functions:
            secu += ["--functions", args.functions]
    else:
        secu += ["--offline"]
    steps.append(("Sécurité", secu))

    if not args.skip_review:
        steps.append(("Revue visuelle", [
            str(HERE / "review_site.py"), args.url, "--out", args.out,
        ]))

    failed = []
    for label, command in steps:
        if not run(label, command):
            failed.append(label)
            # Le poids et les chiffres sont des préalables : inutile d'aller plus loin.
            if label in ("Poids du build", "Chiffres affichés"):
                break

    print(f"\n{'=' * 68}")
    if failed:
        print("RÉSULTAT : NE PAS DÉPLOYER — " + ", ".join(failed))
        print("Corrige, relance ce script. Il n'y a pas d'autre porte.")
        sys.exit(1)
    print("RÉSULTAT : PRÊT À DÉPLOYER.")
    print("Il reste une chose qu'aucun script ne fait à ta place : ouvrir les captures")
    print(f"de {args.out} et les critiquer en directeur artistique.")
    sys.exit(0)


if __name__ == "__main__":
    main()
