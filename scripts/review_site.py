#!/usr/bin/env python3
"""Revue visuelle d'un site en local ou en ligne, pour la boucle critique → correction.

Capture desktop (1440x900) et mobile (390x844) à plusieurs profondeurs de défilement,
teste la version légère (?lite=1), relève les erreurs console, les images cassées,
les textes restés entre crochets, les cibles tactiles trop petites, les champs de
saisie sous 16 px — sous ce seuil, Safari iOS zoome toute la page à la saisie —
et les images trop petites pour l'écran, qui paraissent floues sans que rien
dans le code ne le laisse deviner.
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
    "mobile": {"width": 390, "height": 844, "is_mobile": True, "has_touch": True,
               # 3 et non 2 : c'est la densite des telephones vendus depuis
               # des annees, et c'est a 3 que le manque de definition se voit.
               "device_scale_factor": 3},
}

AUDIT_JS = """
() => {
  // Le texte entre crochets signale un trou laisse dans un gabarit. Mais
  // une sortie machine en contient legitimement — « [blocking] », « [ok] »,
  // un niveau de log — et elle est reproduite mot pour mot par principe. On
  // retire donc <pre> et <code> avant de chercher.
  const sansMachine = document.body.cloneNode(true);
  sansMachine.querySelectorAll('pre, code, kbd, samp').forEach((n) => n.remove());
  const text = sansMachine.innerText || '';
  const placeholders = [...new Set((text.match(/\\[[^\\]\\n]{3,80}\\]/g) || []))].slice(0, 20);
  const brokenImages = [...document.images]
    .filter(img => img.complete && img.naturalWidth === 0 && !img.src.startsWith('data:'))
    .map(img => img.getAttribute('src')).slice(0, 20);
  // Hors tabulation ou sous aria-hidden : un piege a robots, un element
  // masque aux technologies d'assistance. Personne ne peut l'atteindre,
  // donc sa taille ne veut rien dire.
  const atteignable = (el) =>
    el.getAttribute('tabindex') !== '-1' && !el.closest('[aria-hidden="true"]');
  const smallTargets = [...document.querySelectorAll('a, button, summary, input, select')]
    .filter(atteignable)
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && (r.height < 44 || r.width < 44); })
    .map(el => (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 40)).slice(0, 15);
  const smallFontInputs = [...document.querySelectorAll('input, select, textarea')]
    .filter(atteignable)
    .filter(el => {
      if (el.type === 'hidden' || el.offsetParent === null) return false;
      return parseFloat(getComputedStyle(el).fontSize) < 16;
    })
    .map(el => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''} `
               + `(${parseFloat(getComputedStyle(el).fontSize)}px)`)
    .slice(0, 10);
  // Une image trop petite pour l'ecran est indistinguable d'une image trop
  // compressee : meme flou, meme reproche du client. Le navigateur connait les
  // deux nombres, il suffit de les lui demander.
  const ratio = window.devicePixelRatio || 1;
  // Le seuil suit l'ecran, et s'arrete a 2. En dessous de la densite reelle,
  // le navigateur etire le fichier : c'est la que le flou apparait. Au-dela de
  // 2 le gain cesse d'etre visible et on ne ferait qu'alourdir la page — un
  // controle qui reclame l'inutile finit par etre ignore.
  const exige = Math.min(ratio, 2);

  // La largeur REELLE du fichier, et non celle que le DOM annonce.
  //
  // Piege corrige ici : sur une image choisie dans un srcset en « w »,
  // naturalWidth est DEJA divise par la densite que le navigateur a calculee.
  // Il vaut donc toujours a peu pres la largeur d'affichage, et le controle
  // comparait une valeur a elle-meme : il ne pouvait rien trouver, et criait
  // au flou sur chaque image d'un ecran dense. Un controle qui se trompe dans
  // les deux sens ne mesure rien.
  //
  // La seule source fiable est le descripteur « w » de l'entree qui correspond
  // a currentSrc. A defaut de srcset, naturalWidth dit vrai.
  const largeurReelle = (img) => {
    const choisi = img.currentSrc || img.src;
    // TOUS les jeux du <picture>, pas un seul : le fichier retenu vient
    // souvent d'une <source> (AVIF, WebP) alors que l'<img> porte le repli
    // JPEG. Chercher dans un seul des deux, c'est ne jamais trouver la bonne
    // entree sur les navigateurs modernes — et retomber en silence sur la
    // mesure fausse qu'on voulait justement corriger.
    const jeux = [];
    const propre = img.getAttribute('srcset');
    if (propre) jeux.push(propre);
    const pere = img.closest('picture');
    if (pere) {
      pere.querySelectorAll('source[srcset]').forEach((s) => jeux.push(s.getAttribute('srcset')));
    }
    for (const jeu of jeux) {
      for (const entree of jeu.split(',')) {
        const bouts = entree.trim().split(/\\s+/);
        if (!bouts[0]) continue;
        const largeur = /^([0-9]+)w$/.exec(bouts[1] || '');
        if (largeur && new URL(bouts[0], location.href).href === choisi) {
          return parseInt(largeur[1], 10);
        }
      }
    }
    return img.naturalWidth;
  };

  const softImages = [...document.images]
    .filter((img) => {
      const w = img.getBoundingClientRect().width;
      return w > 40 && img.naturalWidth > 0 && largeurReelle(img) < w * exige;
    })
    .map((img) => {
      const w = Math.round(img.getBoundingClientRect().width);
      const reelle = largeurReelle(img);
      return `${(img.currentSrc || img.src).split('/').pop()} `
        + `(affichee ${w} px, fichier ${reelle} px, `
        + `${(reelle / w).toFixed(1)}x, il en faut ${exige})`;
    })
    .slice(0, 12);
  // Une image rognee sans qu'on l'ait voulu.
  //
  // Defaut trouve le 13 septembre 2026 : des attributs width/height sur la
  // balise, sans « height: auto » en CSS, et la hauteur de l'attribut devient
  // la hauteur utilisee. Une photo 3:4 posee dans une colonne de 424 px
  // s'affichait en 424x1280 ; object-fit: cover mangeait les trois quarts du
  // sujet. La page restait belle, nette, dans les budgets — et amputee.
  //
  // Aucun autre controle ne pouvait le voir : le poids etait bon, la densite
  // etait bonne, le contraste etait bon. Seul l'ecart entre le format de la
  // boite et celui du fichier le dit.
  //
  // Le seuil est large (25 %) : un recadrage assume existe et n'est pas une
  // faute. Ce qu'on cherche, c'est l'amputation involontaire.
  const croppedImages = [...document.images]
    .filter((img) => {
      const b = img.getBoundingClientRect();
      if (b.width < 40 || b.height < 40) return false;
      if (!img.naturalWidth || !img.naturalHeight) return false;
      const boite = b.width / b.height;
      const source = img.naturalWidth / img.naturalHeight;
      return Math.abs(boite - source) / source > 0.25;
    })
    .map((img) => {
      const b = img.getBoundingClientRect();
      const boite = b.width / b.height;
      const source = img.naturalWidth / img.naturalHeight;
      const perdu = Math.round((1 - Math.min(boite, source) / Math.max(boite, source)) * 100);
      return `${(img.currentSrc || img.src).split('/').pop()} `
        + `(boite ${Math.round(b.width)}x${Math.round(b.height)} = ${boite.toFixed(2)}, `
        + `fichier ${source.toFixed(2)}, ${perdu}% du sujet hors cadre)`;
    })
    .slice(0, 12);

  const h1 = document.querySelectorAll('h1').length;
  const missingAlt = [...document.images].filter(img => !img.hasAttribute('alt')).length;
  return { placeholders, brokenImages, smallTargets, smallFontInputs, h1Count: h1,
           imagesWithoutAlt: missingAlt, softImages, croppedImages, devicePixelRatio: ratio,
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
        if data.get("croppedImages"):
            problems += len(data["croppedImages"])
            print(f"⚠ Image(s) rognées sans l'avoir voulu — la boîte n'a pas le format "
                  f"du fichier, le sujet sort du cadre : {data['croppedImages']}")
        if data.get("softImages"):
            problems += len(data["softImages"])
            print(f"⚠ Image(s) trop petites pour l'écran — elles paraîtront floues, "
                  f"et le client l'attribuera à la compression : {data['softImages']}")
        if data["imagesWithoutAlt"]:
            problems += 1
            print(f"⚠ {data['imagesWithoutAlt']} image(s) sans attribut alt")
        print(f"Captures : {len(data['screenshots'])} dans {args.out}")
    print(f"\nRapport : {Path(args.out) / 'report.json'} — {problems} point(s) à corriger. "
          "Ouvre maintenant les captures et critique le rendu.")


if __name__ == "__main__":
    main()
