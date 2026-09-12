#!/usr/bin/env python3
"""Contrôle un média livré — sur le fichier produit, jamais sur la source.

Pourquoi ce script existe : une vidéo coupée se vérifie sur ce qui est servi.
Chercher le point de coupe dans le fichier d'origine avec un positionnement
rapide (`ffmpeg -ss` avant `-i`) tombe sur l'image-clé la plus proche, pas sur
l'image demandée — la coupe part alors d'une mesure fausse, et personne ne s'en
aperçoit tant que le client ne regarde pas la fin.

Le script extrait la première et la dernière image du fichier final, donne la
durée réelle, le poids, la définition et le débit, puis rappelle la seule chose
qui compte : OUVRIR ces deux images et les regarder.

Usage :
  python3 check_media.py studio/assets/video/clip.mp4 --out studio/review
  python3 check_media.py site/public/video/*.mp4 --out studio/review --max-mb 8

Code de sortie 1 si un fichier dépasse le plafond de poids ou n'est pas lisible.
Dépendance : ffmpeg et ffprobe dans le PATH.
"""
import argparse
import json
import shutil
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


def probe(path):
    """Durée, définition, débit et piste audio, lus dans le fichier produit."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_entries", "format=duration,size,bit_rate",
         "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate",
         str(path)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr else "ffprobe a échoué")
    return json.loads(out.stdout)


def frame_at(path, when, destination):
    """Extrait une image en positionnement précis : -i avant -ss, jamais l'inverse."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if when == "last":
        # -sseof est une option d'ENTRÉE : elle se place avant -i, sinon ffmpeg la
        # refuse. Elle lit depuis la fin, donc la vraie dernière image.
        cmd += ["-sseof", "-0.4", "-i", str(path)]
    else:
        # -ss APRÈS -i : positionnement précis, image exacte. Placé avant, ffmpeg
        # saute à l'image-clé la plus proche — c'est ce piège qui fausse les coupes.
        cmd += ["-i", str(path), "-ss", str(when)]
    cmd += ["-frames:v", "1", "-q:v", "2", str(destination)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"   ffmpeg : {result.stderr.strip().splitlines()[-1]}")
    return result.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="Fichiers vidéo livrés")
    ap.add_argument("--out", default="studio/review", help="Où déposer les images extraites")
    ap.add_argument("--max-mb", type=float, default=10.0, help="Plafond de poids par fichier")
    args = ap.parse_args()

    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        sys.exit("ffmpeg et ffprobe sont requis et introuvables dans le PATH.")

    out = Path(args.out)
    problems = 0

    for name in args.files:
        path = Path(name)
        print(f"\n== {path.name} ==")
        if not path.exists():
            print("❌ Fichier introuvable.")
            problems += 1
            continue
        try:
            data = probe(path)
        except RuntimeError as exc:
            print(f"❌ Illisible : {exc}")
            problems += 1
            continue

        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        size_mb = int(fmt.get("size", 0)) / 1024 / 1024
        video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

        print(f"   durée      : {duration:.2f} s")
        print(f"   définition : {video.get('width')}x{video.get('height')} ({video.get('codec_name')})")
        print(f"   poids      : {size_mb:.2f} Mo")
        print(f"   audio      : {audio.get('codec_name') if audio else 'aucun'}")

        if size_mb > args.max_mb:
            print(f"❌ Dépasse le plafond de {args.max_mb} Mo — à recompresser, "
                  "ou à ne charger qu'au clic.")
            problems += 1

        first = out / f"{path.stem}-premiere.jpg"
        last = out / f"{path.stem}-derniere.jpg"
        ok_first = frame_at(path, 0.1, first)
        ok_last = frame_at(path, "last", last)
        if ok_first and ok_last:
            print(f"   première image : {first}")
            print(f"   DERNIÈRE image : {last}")
        else:
            print("❌ Extraction des images impossible.")
            problems += 1

    print(f"\n{problems} problème(s).")
    print("OUVRE MAINTENANT la dernière image de chaque fichier. Une coupe se juge là,")
    print("pas dans la source : c'est ce que le visiteur verra en dernier.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
