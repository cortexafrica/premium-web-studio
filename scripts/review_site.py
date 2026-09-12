#!/usr/bin/env python3
"""Revue visuelle d'un site en local ou en ligne, pour la boucle critique → correction.

Capture desktop (1440x900) et mobile (390x844) à plusieurs profondeurs de défilement,
teste la version légère (?lite=1), relève les erreurs console, les images cassées,
les textes restés entre crochets, les cibles tactiles trop petites et les champs de
saisie sous 16 px — sous ce seuil, Safari iOS zoome toute la page à la saisie.
Une troisième passe tourne sous WebKit, le moteur de Safari : c'est ce que voit un
iPhone, et Chromium ne le reproduit pas.
Ouvre ensuite les captures produites et critique-les réellement : c'est le but.

Usage :
  python3 review_site.py http://localhost:4173 --out studio/review [--steps 6] [--no-lite] [--no-safari]

Dépendances : pip install playwright && python -m playwright install chromium webkit
(à défaut, faire la même revue avec le MCP Playwright).
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Une console Windows repond souvent en cp1252 : le premier caractere non
# latin-1 affiche interrompt le script et le controle ne rend aucun verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit("Playwright manquant : pip install playwright && python -m playwright install chromium")

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844, "is_mobile": True, "has_touch": True, "device_scale_factor": 2},
}

AUDIT_JS = """
() => {
  const text = document.body.innerText;
  const placeholders = [...new Set((text.match(/\\[[^\\]\\n]{3,80}\\]/g) || []))].slice(0, 20);
  const brokenImages = [...document.images]
    .filter(img => img.complete && img.naturalWidth === 0 && !img.src.startsWith('data:'))
    .map(img => img.getAttribute('src')).slice(0, 20);
  const smallTargets = [...document.querySelectorAll('a, button, summary, input, select')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && (r.height < 44 || r.width < 44); })
    .map(el => (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 40)).slice(0, 15);
  const smallFontInputs = [...document.querySelectorAll('input, select, textarea')]
    .filter(el => {
      if (el.type === 'hidden' || el.offsetParent === null) return false;
      return parseFloat(getComputedStyle(el).fontSize) < 16;
    })
    .map(el => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''} `
               + `(${parseFloat(getComputedStyle(el).fontSize)}px)`)
    .slice(0, 10);
  const h1 = document.querySelectorAll('h1').length;
  const missingAlt = [...document.images].filter(img => !img.hasAttribute('alt')).length;
  return { placeholders, brokenImages, smallTargets, smallFontInputs, h1Count: h1,
           imagesWithoutAlt: missingAlt,
           title: document.title, pageHeight: document.documentElement.scrollHeight };
}
"""


async def run_viewport(browser, label, viewport, url, out, steps, lite):
    """Une passe : un moteur, une taille d'écran, des captures et un audit."""
    opts = dict(viewport)
    size = {"width": opts.pop("width"), "height": opts.pop("height")}
    context = await browser.new_context(viewport=size, **opts)
    page = await context.new_page()
    errors = []
    page.on("console", lambda m, e=errors: e.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda exc, e=errors: e.append(str(exc)))
    page.on("requestfailed", lambda r, e=errors: e.append(f"requête échouée : {r.url}"))

    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(1500)
    height = await page.evaluate("document.documentElement.scrollHeight - innerHeight")
    shots = []
    for i in range(steps + 1):
        y = int(height * i / steps)
        await page.evaluate(f"window.scrollTo(0, {y})")
        await page.wait_for_timeout(900)
        path = out / f"{label}-{i:02d}.png"
        await page.screenshot(path=str(path))
        shots.append(str(path))
    audit = await page.evaluate(AUDIT_JS)
    result = {"screenshots": shots, "errors": errors[:20], **audit}

    if lite:
        lite_page = await context.new_page()
        sep = "&" if "?" in url else "?"
        await lite_page.goto(f"{url}{sep}lite=1", wait_until="networkidle")
        await lite_page.wait_for_timeout(800)
        lite_path = out / f"{label}-lite.png"
        await lite_page.screenshot(path=str(lite_path), full_page=True)
        result["lite_screenshot"] = str(lite_path)
    await context.close()
    return result


async def review(url, out, steps, lite, safari=True):
    out.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "viewports": {}, "notes": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name, viewport in VIEWPORTS.items():
            report["viewports"][name] = await run_viewport(
                browser, name, viewport, url, out, steps, lite)
        await browser.close()

        # Passe WebKit : c'est le moteur de Safari, donc celui de tout iPhone.
        # Chromium ne reproduit ni son rendu de police, ni ses règles de zoom,
        # ni son traitement du clavier virtuel.
        if safari:
            try:
                wk = await p.webkit.launch()
            except Exception as exc:
                report["notes"].append(
                    "Passe Safari non exécutée : " + str(exc).splitlines()[0]
                    + " — installe-le avec « python -m playwright install webkit ».")
            else:
                report["viewports"]["safari-mobile"] = await run_viewport(
                    wk, "safari-mobile", VIEWPORTS["mobile"], url, out, steps, False)
                await wk.close()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", default="studio/review")
    ap.add_argument("--steps", type=int, default=6, help="Nombre d'intervalles de défilement capturés")
    ap.add_argument("--no-lite", action="store_true")
    ap.add_argument("--no-safari", action="store_true",
                    help="Saute la passe WebKit (moteur de Safari et de tout iPhone)")
    args = ap.parse_args()

    try:
        report = asyncio.run(review(args.url, Path(args.out), args.steps,
                                    not args.no_lite, not args.no_safari))
    except Exception as exc:  # serveur éteint, URL fausse, navigateur absent…
        sys.exit(f"Revue impossible : {str(exc).splitlines()[0]}\n"
                 "→ Vérifie que le site tourne (npm run preview / npm run dev) et que Chromium est installé "
                 "(python -m playwright install chromium).")
    (Path(args.out) / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    problems = 0
    for note in report.get("notes", []):
        print(f"ℹ {note}")
    for name, data in report["viewports"].items():
        print(f"\n== {name} ==")
        for key, label in (("errors", "Erreurs console/réseau"), ("placeholders", "Textes non remplacés"),
                           ("brokenImages", "Images cassées"), ("smallTargets", "Cibles tactiles < 44 px")):
            if data[key]:
                problems += len(data[key]) if key != "smallTargets" or name == "mobile" else 0
                print(f"⚠ {label} : {data[key]}")
        if data.get("smallFontInputs"):
            problems += len(data["smallFontInputs"])
            print(f"⚠ Champs sous 16 px — Safari iOS zoomera la page à la saisie : "
                  f"{data['smallFontInputs']}")
        if data["h1Count"] != 1:
            problems += 1
            print(f"⚠ {data['h1Count']} balise(s) h1 (attendu : 1)")
        if data["imagesWithoutAlt"]:
            problems += 1
            print(f"⚠ {data['imagesWithoutAlt']} image(s) sans attribut alt")
        print(f"Captures : {len(data['screenshots'])} dans {args.out}")
    print(f"\nRapport : {Path(args.out) / 'report.json'} — {problems} point(s) à corriger. "
          "Ouvre maintenant les captures et critique le rendu.")


if __name__ == "__main__":
    main()
