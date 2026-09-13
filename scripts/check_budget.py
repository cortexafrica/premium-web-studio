#!/usr/bin/env python3
"""Contrôle le poids d'un site construit (dossier dist/, out/, build/) contre des budgets.

Sépare le poids INITIAL (ce que le visiteur télécharge pour voir la page) des séquences
d'images chargées progressivement (dossier frames/). Code de sortie 1 si un budget est dépassé.

Usage :
  python3 check_budget.py dist [--js-kb 220] [--css-kb 60] [--image-kb 350]
      [--initial-mb 1.8] [--frames-desktop-mb 12] [--frames-mobile-mb 5] [--json]

Budgets par défaut pensés pour des visiteurs mobiles en 4G moyenne ou data limitée.
JS et CSS sont mesurés compressés (gzip), comme servis par un hébergeur.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

# Une console Windows repond souvent en cp1252 : le premier caractere non
# latin-1 affiche interrompt le script et le controle ne rend aucun verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

IMG = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg"}
VIDEO = {".mp4", ".webm", ".mov"}
FONT = {".woff", ".woff2", ".ttf", ".otf"}


def gz(path):
    return len(gzip.compress(path.read_bytes(), compresslevel=6))


# Un jeu d'images responsive compte pour UNE image, pas pour la somme de ses
# variantes.
#
# Le defaut corrige ici : le script additionnait tous les fichiers du dossier.
# Une image declinee en quatre largeurs et deux formats y pese huit fois, alors
# qu'un visiteur en telecharge exactement une. Le budget etait donc depasse par
# la bonne pratique elle-meme — et un controle qui punit la bonne pratique finit
# par etre desactive, ce qui est pire que pas de controle.
#
# Ce qu'on compte a la place : par famille, la PLUS GROSSE variante du format
# que le navigateur choisira reellement. AVIF quand il existe, sinon WebP,
# sinon le format d'origine. C'est le pire cas honnete pour un visiteur a jour,
# et ca reste bloquant si on livre une image trop lourde.
PREFERENCE = (".avif", ".webp")
FAMILLE_RE = re.compile(r"^(.*)-(\d{2,5})$")


def poids_images(images):
    """(poids retenu, familles) — `images` est une liste (chemin, taille, ext)."""
    familles = {}
    for rel, size, ext in images:
        tige = Path(rel).with_suffix("").as_posix()
        m = FAMILLE_RE.match(tige)
        cle = m.group(1) if m else tige
        familles.setdefault(cle, []).append((rel, size, ext))

    total, detail = 0, []
    for cle, membres in sorted(familles.items()):
        formats = {e for _, _, e in membres}
        choisi = next((p for p in PREFERENCE if p in formats), None)
        retenus = [m for m in membres if m[2] == choisi] if choisi else membres
        pire = max(retenus, key=lambda m: m[1])
        total += pire[1]
        if len(membres) > 1:
            detail.append((cle, len(membres), pire[0], pire[1]))
    return total, detail


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dist")
    ap.add_argument("--js-kb", type=float, default=220)
    ap.add_argument("--css-kb", type=float, default=60)
    ap.add_argument("--image-kb", type=float, default=350, help="Poids max d'une image hors séquences")
    ap.add_argument("--initial-mb", type=float, default=1.8, help="Total hors frames/ et vidéos")
    ap.add_argument("--frames-desktop-mb", type=float, default=12)
    ap.add_argument("--frames-mobile-mb", type=float, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.dist)
    if not root.is_dir():
        sys.exit(f"Dossier introuvable : {root}")

    totals = {"js_gz": 0, "css_gz": 0, "images": 0, "fonts": 0, "video": 0, "other": 0,
              "frames_desktop": 0, "frames_mobile": 0}
    heavy_images, videos, images = [], [], []

    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        size, ext = f.stat().st_size, f.suffix.lower()
        if "/frames/" in f"/{rel}" or rel.startswith("frames/"):
            if "/mobile/" in f"/{rel}":
                totals["frames_mobile"] += size
            elif "/desktop/" in f"/{rel}":
                totals["frames_desktop"] += size
            continue
        if ext in (".js", ".mjs"):
            totals["js_gz"] += gz(f)
        elif ext == ".css":
            totals["css_gz"] += gz(f)
        elif ext in IMG:
            images.append((rel, size, ext))
            if size > args.image_kb * 1000:
                heavy_images.append((rel, size))
        elif ext in FONT:
            totals["fonts"] += size
        elif ext in VIDEO:
            totals["video"] += size
            videos.append((rel, size))
        elif ext not in (".map",):
            totals["other"] += size

    totals["images"], familles = poids_images(images)

    initial = totals["js_gz"] + totals["css_gz"] + totals["images"] + totals["fonts"] + totals["other"]
    checks = [
        ("JS (gzip)", totals["js_gz"], args.js_kb * 1000),
        ("CSS (gzip)", totals["css_gz"], args.css_kb * 1000),
        ("Poids initial (hors séquences et vidéos)", initial, args.initial_mb * 1_000_000),
        ("Séquence desktop", totals["frames_desktop"], args.frames_desktop_mb * 1_000_000),
        ("Séquence mobile", totals["frames_mobile"], args.frames_mobile_mb * 1_000_000),
    ]
    if familles:
        print("Jeux d'images responsive — une seule variante comptee par jeu :")
        for cle, n, pire, taille in familles:
            print(f"  {cle}  {n} fichiers  ->  {Path(pire).name} ({taille/1000:.0f} Ko)")
        print()

    failures = [c for c in checks if c[1] > c[2]]
    if heavy_images:
        failures.append(("Images trop lourdes", len(heavy_images), 0))

    fmt = lambda b: f"{b / 1_000_000:.2f} Mo" if b >= 1_000_000 else f"{b / 1000:.0f} Ko"
    report = {
        "checks": [{"name": n, "value": fmt(v), "budget": fmt(b), "ok": v <= b} for n, v, b in checks],
        "heavy_images": [{"file": r, "size": fmt(s)} for r, s in sorted(heavy_images, key=lambda x: -x[1])[:15]],
        "videos": [{"file": r, "size": fmt(s)} for r, s in videos],
        "fonts": fmt(totals["fonts"]),
        "passed": not failures,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for c in report["checks"]:
            print(f"{'✅' if c['ok'] else '❌'} {c['name']}: {c['value']} (budget {c['budget']})")
        for img in report["heavy_images"]:
            print(f"❌ Image > {args.image_kb:.0f} Ko : {img['file']} ({img['size']})")
        for v in report["videos"]:
            print(f"ℹ Vidéo : {v['file']} ({v['size']}) — vérifier preload=\"none\" ou metadata et poster")
        print("RÉSULTAT :", "OK" if report["passed"] else "BUDGET DÉPASSÉ")
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
