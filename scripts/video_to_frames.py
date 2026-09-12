#!/usr/bin/env python3
"""Transforme une ou plusieurs vidéos en séquences d'images optimisées pour un site à défilement.

Produit, dans --out :
  desktop/frame_0001.webp …   (paysage)
  mobile/frame_0001.webp …    (portrait recadré au centre, ou vidéo mobile dédiée)
  poster-desktop.webp / poster-mobile.webp  (image fixe : chargement initial + mode data léger)
  manifest.json               (lu par le composant ScrollSequence du template)

Plusieurs vidéos (--input a.mp4 --input b.mp4) sont enchaînées dans l'ordre en une seule séquence.

Usage :
  python3 video_to_frames.py --input hero.mp4 --out public/frames \
      [--desktop-frames 120] [--mobile-frames 72] [--desktop-width 1600] [--mobile-width 720] \
      [--mobile-input hero-9x16.mp4] [--mobile-aspect 9:16] [--quality 72] [--public-prefix /frames]

Dépendances : ffmpeg + ffprobe avec libwebp.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"Échec : {' '.join(cmd)}\n{proc.stderr[-2000:]}")
    return proc.stdout


def probe(path):
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate:format=duration", "-of", "json", str(path),
    ])
    data = json.loads(out)
    stream = data["streams"][0]
    num, _, den = stream.get("avg_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return float(data["format"]["duration"]), int(stream["width"]), int(stream["height"]), fps


def concat(inputs, workdir):
    """Enchaîne plusieurs clips (réencodage pour éviter les incompatibilités de codecs)."""
    if len(inputs) == 1:
        return Path(inputs[0])
    _, w, h, _ = probe(inputs[0])
    w, h = w - w % 2, h - h % 2
    out = workdir / "concat.mp4"
    cmd = ["ffmpeg", "-y"]
    for i in inputs:
        cmd += ["-i", str(i)]
    filters = "".join(
        f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=30[v{i}];"
        for i in range(len(inputs))
    )
    filters += "".join(f"[v{i}]" for i in range(len(inputs))) + f"concat=n={len(inputs)}:v=1:a=0[out]"
    cmd += ["-filter_complex", filters, "-map", "[out]", "-an", "-c:v", "libx264", "-crf", "16", str(out)]
    run(cmd)
    return out


def extract(src, dest, frames, width, quality, crop_aspect=None):
    duration, w, h, src_fps = probe(src)
    available = int(duration * src_fps)
    if frames > available:
        print(f"⚠ {dest.name} : {frames} images demandées mais la vidéo n'en contient que ~{available} ; "
              f"plafonné à {available} (au-delà, ce ne seraient que des doublons).", file=sys.stderr)
        frames = available
    fps = max(frames / duration, 1)
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("frame_*.webp"):
        old.unlink()

    vf = []
    effective_w = w
    if crop_aspect:
        aw, ah = crop_aspect
        target_ratio = aw / ah
        if w / h > target_ratio:  # source trop large : on rogne les côtés
            effective_w = int(h * aw / ah) // 2 * 2
            vf.append(f"crop={effective_w}:ih")
        else:
            vf.append(f"crop=iw:{int(w * ah / aw) // 2 * 2}")
    if width > effective_w:
        advice = ("génère un clip vertical dédié (--mobile-input)" if crop_aspect
                  else "génère la vidéo en résolution plus haute")
        print(f"⚠ {dest.name} : source trop petite ({effective_w}px utiles), largeur ramenée de {width} à "
              f"{effective_w}px pour éviter l'agrandissement. Pour une image nette, {advice}.", file=sys.stderr)
        width = effective_w
    vf += [f"fps={fps:.5f}", f"scale={width}:-2:flags=lanczos"]

    run([
        "ffmpeg", "-y", "-i", str(src), "-vf", ",".join(vf), "-frames:v", str(frames),
        "-c:v", "libwebp", "-quality", str(quality), "-compression_level", "6",
        str(dest / "frame_%04d.webp"),
    ])
    files = sorted(dest.glob("frame_*.webp"))
    if not files:
        sys.exit(f"Aucune image produite dans {dest}")
    first = files[0]
    total_bytes = sum(f.stat().st_size for f in files)
    probe_out = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "json", str(first),
    ]))["streams"][0]
    return {
        "count": len(files),
        "width": probe_out["width"],
        "height": probe_out["height"],
        "bytes": total_bytes,
    }


def poster(frames_dir, target, width, quality):
    first = sorted(frames_dir.glob("frame_*.webp"))[0]
    run(["ffmpeg", "-y", "-i", str(first), "-vf", f"scale={width}:-2", "-c:v", "libwebp",
         "-quality", str(min(quality + 10, 90)), str(target)])
    return target.stat().st_size


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", action="append", required=True, help="Vidéo source (répétable, dans l'ordre)")
    p.add_argument("--mobile-input", action="append", help="Vidéo(s) verticale(s) dédiée(s) au mobile")
    p.add_argument("--out", required=True)
    p.add_argument("--desktop-frames", type=int, default=120)
    p.add_argument("--mobile-frames", type=int, default=72)
    p.add_argument("--desktop-width", type=int, default=1600)
    p.add_argument("--mobile-width", type=int, default=720)
    p.add_argument("--mobile-aspect", default="9:16", help="Recadrage centre si pas de --mobile-input")
    p.add_argument("--quality", type=int, default=72)
    p.add_argument("--public-prefix", default="/frames", help="Chemin public servi par le site")
    args = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} introuvable : installe ffmpeg")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prefix = args.public_prefix.rstrip("/")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        desktop_src = concat(args.input, tmp)
        desktop = extract(desktop_src, out / "desktop", args.desktop_frames, args.desktop_width, args.quality)

        if args.mobile_input:
            mobile_dir = tmp / "mobile"
            mobile_dir.mkdir()
            mobile_src, crop = concat(args.mobile_input, mobile_dir), None
        else:
            aw, ah = (int(x) for x in args.mobile_aspect.split(":"))
            mobile_src, crop = desktop_src, (aw, ah)
        mobile = extract(mobile_src, out / "mobile", args.mobile_frames, args.mobile_width, args.quality - 4, crop)

    poster_d = poster(out / "desktop", out / "poster-desktop.webp", args.desktop_width, args.quality)
    poster_m = poster(out / "mobile", out / "poster-mobile.webp", args.mobile_width, args.quality)

    manifest = {
        "desktop": {**desktop, "pattern": f"{prefix}/desktop/frame_{{index}}.webp", "poster": f"{prefix}/poster-desktop.webp"},
        "mobile": {**mobile, "pattern": f"{prefix}/mobile/frame_{{index}}.webp", "poster": f"{prefix}/poster-mobile.webp"},
        "indexPadding": 4,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def mb(b):
        return f"{b / 1_000_000:.1f} Mo" if b >= 1_000_000 else f"{b / 1000:.0f} Ko"
    print(json.dumps({
        "manifest": str(out / "manifest.json"),
        "desktop": f"{desktop['count']} images {desktop['width']}x{desktop['height']} — {mb(desktop['bytes'])}",
        "mobile": f"{mobile['count']} images {mobile['width']}x{mobile['height']} — {mb(mobile['bytes'])}",
        "posters": f"{mb(poster_d)} / {mb(poster_m)}",
    }, indent=2, ensure_ascii=False))
    if mobile["bytes"] > 6_000_000:
        print("⚠ Séquence mobile > 6 Mo : réduire --mobile-frames, --mobile-width ou --quality.", file=sys.stderr)


if __name__ == "__main__":
    main()
