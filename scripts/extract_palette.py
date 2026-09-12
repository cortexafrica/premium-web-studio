#!/usr/bin/env python3
"""Extrait une palette de marque exploitable depuis une image (produit, logo, photo).

Sortie : JSON (couleurs triées par présence, luminance, saturation, rôles proposés,
contrastes WCAG) + bloc CSS prêt à coller. Les rôles sont une PROPOSITION de départ :
la direction artistique décide ensuite.

Usage :
    python3 extract_palette.py photo.jpg [--colors 8] [--out palette.json]
Dépendance : Pillow (pip install pillow)
"""
import argparse
import colorsys
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow manquant : pip install pillow")


def hex_of(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def rel_luminance(rgb):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((rel_luminance(a), rel_luminance(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def extract(path, n_colors):
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        # Les zones transparentes (logos PNG) ne doivent pas peser dans la palette
        alpha = img.split()[-1]
        img = Image.composite(img, background, alpha).convert("RGB")
    else:
        img = img.convert("RGB")

    img.thumbnail((240, 240))
    quantized = img.quantize(colors=max(n_colors * 2, 12), method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    counts = sorted(quantized.getcolors(), reverse=True)  # [(count, index)]
    total = sum(c for c, _ in counts)

    colors = []
    for count, idx in counts:
        rgb = tuple(palette[idx * 3: idx * 3 + 3])
        # Fusionne les teintes quasi identiques
        match = next((c for c in colors if distance(c["rgb"], rgb) < 28), None)
        if match:
            match["share"] += count / total
            continue
        colors.append({"rgb": rgb, "share": count / total})
        if len(colors) >= n_colors:
            break

    for c in colors:
        h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in c["rgb"]))
        c.update(
            hex=hex_of(c["rgb"]),
            share=round(c["share"], 3),
            luminance=round(rel_luminance(c["rgb"]), 3),
            saturation=round(s, 3),
            hue=round(h * 360),
        )
    return colors


def propose_roles(colors):
    by_lum = sorted(colors, key=lambda c: c["luminance"])
    ink, paper = by_lum[0], by_lum[-1]
    candidates = [c for c in colors if c not in (ink, paper) and c["saturation"] > 0.25]
    accent = max(candidates, key=lambda c: c["saturation"] * (0.5 + c["share"]), default=None)
    supports = [c for c in colors if c not in (ink, paper, accent)]
    roles = {"ink": ink["hex"], "paper": paper["hex"]}
    if accent:
        roles["accent"] = accent["hex"]
    if supports:
        roles["surface"] = supports[0]["hex"]
    return roles, ink, paper, accent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image")
    parser.add_argument("--colors", type=int, default=8)
    parser.add_argument("--out", help="Écrit aussi le JSON dans ce fichier")
    args = parser.parse_args()

    if not Path(args.image).exists():
        sys.exit(f"Fichier introuvable : {args.image}")

    colors = extract(args.image, args.colors)
    roles, ink, paper, accent = propose_roles(colors)

    checks = {"ink_on_paper": contrast(ink["rgb"], paper["rgb"])}
    if accent:
        checks["accent_on_paper"] = contrast(accent["rgb"], paper["rgb"])
        checks["accent_on_ink"] = contrast(accent["rgb"], ink["rgb"])

    warnings = []
    if checks["ink_on_paper"] < 4.5:
        warnings.append("Contraste texte/fond < 4.5 : assombrir ink ou éclaircir paper avant usage pour du texte.")
    if accent and max(checks["accent_on_paper"], checks["accent_on_ink"]) < 3:
        warnings.append("Accent peu lisible sur les deux fonds : le réserver aux aplats, jamais au texte.")

    result = {
        "source": args.image,
        "colors": [{k: v for k, v in c.items() if k != "rgb"} for c in colors],
        "proposed_roles": roles,
        "contrast": checks,
        "warnings": warnings,
        "css": ":root {\n" + "\n".join(f"  --color-{k}: {v};" for k, v in roles.items()) + "\n}",
    }

    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
