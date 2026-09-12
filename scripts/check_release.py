#!/usr/bin/env python3
"""Contrôle de livraison : ce qui sépare un site fini d'un site presque fini.

Aucun de ces points n'est visible en regardant la page. Tous se voient ailleurs :
dans l'onglet du navigateur, dans un lien partagé sur WhatsApp, dans les résultats
de recherche, sur une URL fausse, ou dans l'œil d'un lecteur du marché visé.

Il vérifie :
  - la favicon, déclarée ET réellement servie ;
  - l'image de partage en URL absolue, servie, aux dimensions déclarées ;
  - l'adresse canonique, og:url, og:title, og:description, la méta description ;
  - un titre de page utile et l'attribut lang ;
  - une mention légale en pied de page ;
  - une page 404 propre dans le build ;
  - l'orthographe du marché visé (--market us interdit l'anglais britannique) ;
  - les unités métriques nues sur un marché impérial ;
  - les liens : un lien interne mort est bloquant, un lien externe mort est
    signalé (un catalogue tombé ne casse pas la page, il coupe la vente) ;
  - les contradictions entre deux affirmations de la même page.

Usage :
  python3 check_release.py http://localhost:4173/ --dist site/dist --market us
  python3 check_release.py https://exemple.com --market us --claims studio/claims.json

Code de sortie 1 dès qu'un point bloquant échoue.
Dépendances : playwright (+ chromium) et Pillow pour mesurer l'image de partage.
"""
import argparse
import asyncio
import json
import re
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

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

# --- Orthographe : ce qui trahit un site écrit pour un autre marché -----------
BRITISH = {
    r"\bcatalogue\b": "catalog",
    r"\bjewellery\b": "jewelry",
    r"\bcolour(s|ed|ing)?\b": "color",
    r"\bfavourite(s)?\b": "favorite",
    r"\bcentre(s)?\b": "center",
    r"\bmetre(s)?\b": "meter",
    r"\blitre(s)?\b": "liter",
    r"\blabour\b": "labor",
    r"\bneighbour(s|hood)?\b": "neighbor",
    r"\bprogramme(s)?\b": "program",
    r"\bcancelled\b": "canceled",
    r"\btravelled\b": "traveled",
    r"\benquiry\b": "inquiry",
    r"\b\w+is(e|ed|ing|ation)\b": "graphie en -ize / -ization",
}
# Faux positifs de la règle en -ise : ces mots s'écrivent ainsi des deux côtés.
ISE_EXCEPTIONS = {
    "advertise", "advertised", "advertising", "advise", "advised", "advising",
    "comprise", "comprised", "comprising", "exercise", "exercised", "exercising",
    "franchise", "franchised", "franchising", "merchandise", "merchandising",
    "promise", "promised", "promising", "supervise", "supervised", "supervising",
    "surprise", "surprised", "surprising", "rise", "rising", "wise", "otherwise",
    "expertise", "precise", "concise", "raise", "raised", "raising", "praise",
    "noise", "cruise", "paradise", "compromise", "enterprise", "premise",
    "revise", "revised", "revising", "devise", "despise", "arise", "arising",
}

# Une devise etrangere au marche vise trahit un texte recycle d'une version
# precedente : « one-euro product line » sur un site qui facture en dollars.
CURRENCY = {"us": ("euro", "euros", "€", "EUR", "pound", "sterling", "£"),
            "fr": ("dollar", "dollars", "$", "USD"),
            "uk": ("dollar", "dollars", "$", "USD", "euro", "€")}

METRIC_RE = re.compile(r"\b\d[\d.,\s]*\s?(sqm|m²|m2|km|cm|mm|kg|litre|liter|l)\b", re.IGNORECASE)
IMPERIAL_RE = re.compile(r"\b(sq ft|sqft|square feet|ft|inch|inches|miles?|lb|lbs|oz|gallon)\b", re.IGNORECASE)

# --- Contradictions : deux affirmations qui ne peuvent pas coexister ----------
DEFAULT_CLAIMS = [
    [r"no per[- ]item minimum|there is no minimum per item",
     r"minimum quantity per item|its own minimum quantity|minimum per item is shown"],
    [r"\bno minimum order\b", r"\bminimum order\b.{0,40}\d"],
    [r"\bfree shipping\b", r"shipping (is )?(excluded|not included)"],
    [r"no account (is )?needed", r"(create|open) (an )?account to (see|browse|order)"],
    [r"\bin stock\b.{0,30}\ball items\b", r"\bout of stock\b|\bmade to order\b"],
]

COLLECT_JS = """
() => {
  const meta = (sel, attr) => {
    const el = document.querySelector(sel);
    return el ? (el.getAttribute(attr) || '') : null;
  };
  const icons = [...document.querySelectorAll('link[rel~="icon"], link[rel="shortcut icon"]')]
    .map(l => l.getAttribute('href'));
  return {
    title: document.title || '',
    lang: document.documentElement.getAttribute('lang'),
    description: meta('meta[name="description"]', 'content'),
    canonical: meta('link[rel="canonical"]', 'href'),
    ogTitle: meta('meta[property="og:title"]', 'content'),
    ogDescription: meta('meta[property="og:description"]', 'content'),
    ogImage: meta('meta[property="og:image"]', 'content'),
    ogImageWidth: meta('meta[property="og:image:width"]', 'content'),
    ogImageHeight: meta('meta[property="og:image:height"]', 'content'),
    ogUrl: meta('meta[property="og:url"]', 'content'),
    appleIcon: meta('link[rel="apple-touch-icon"]', 'href'),
    icons,
    text: document.body.innerText,
    footerText: (document.querySelector('footer') || {}).innerText || '',
    // textContent et non innerText : un <details> ferme ou une section repliee
    // ne rend aucun innerText, et son contenu compte quand meme pour Google.
    allText: (document.body.textContent || '').replace(/\\s+/g, ' ').trim(),
    jsonLd: [...document.querySelectorAll('script[type="application/ld+json"]')]
      .map((s) => s.textContent || ''),
    // href resolu par le navigateur : on obtient une URL absolue meme quand le
    // document ecrit un chemin relatif.
    links: [...document.querySelectorAll('a[href]')]
      .map((a) => ({ href: a.href, texte: (a.textContent || '').trim().slice(0, 60) }))
      .filter((l) => /^https?:/.test(l.href)),
  };
}
"""

# Une police peut être déclarée, préchargée, téléchargée sans erreur et ne rien
# couvrir : il suffit d'avoir pris le mauvais sous-ensemble chez le fondeur. La
# page tombe alors dans la police système, ce qui passe inaperçu sur un poste de
# travail — la substitution est plausible — et fait ressortir en désordre les
# rares caractères que le fichier contient vraiment.
#
# On ne lit pas le fichier : on mesure. Un caractère composé avec la famille
# déclarée puis avec une police témoin donne deux largeurs différentes si la
# famille le couvre, et exactement la même s'il retombe sur le témoin.
FONT_JS = """
() => {
  const declared = [];
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch { continue; }   // feuille d'un autre domaine
    for (const rule of rules || []) {
      if (rule.constructor.name === 'CSSFontFaceRule') {
        const f = (rule.style.fontFamily || '').replace(/["']/g, '').trim();
        if (f && !declared.includes(f)) declared.push(f);
      }
    }
  }
  if (!declared.length) return { declared, family: '', missing: [], tested: 0 };

  const body = getComputedStyle(document.body).fontFamily.split(',')[0]
    .replace(/["']/g, '').trim();
  const family = declared.includes(body) ? body : declared[0];

  const probe = document.createElement('span');
  probe.style.cssText =
    'position:absolute;left:-9999px;top:0;visibility:hidden;white-space:pre;font-size:96px';
  document.body.appendChild(probe);
  const width = (stack, text) => {
    probe.style.fontFamily = stack;
    probe.textContent = text;
    return probe.getBoundingClientRect().width;
  };

  const seen = new Set(document.body.innerText.replace(/\\s/g, ''));
  const missing = [];
  let tested = 0;
  for (const ch of seen) {
    if (ch.codePointAt(0) < 0x21) continue;

    // Deux témoins, pas un. Avec un seul, un caractère bien couvert dont la
    // largeur coïncide par hasard avec celle du témoin passe pour un repli :
    // « a », « e » et « 7 » l'ont fait. On compose donc le caractère derrière
    // la famille avec deux replis de métriques différentes. S'il est couvert,
    // la famille l'emporte et les deux largeurs sont identiques ; s'il manque,
    // chaque pile suit son propre témoin et les largeurs divergent.
    const mono = width('monospace', ch);
    const serif = width('serif', ch);
    if (Math.abs(mono - serif) < 0.5) continue;   // témoins indiscernables : on ne conclut pas
    tested += 1;
    const viaMono = width('"' + family + '", monospace', ch);
    const viaSerif = width('"' + family + '", serif', ch);
    if (Math.abs(viaMono - viaSerif) > 0.5) missing.push(ch);
  }
  probe.remove();
  return { declared, family, missing, tested };
}
"""


async def collect(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(url, wait_until="networkidle")
        height = await page.evaluate("document.documentElement.scrollHeight")
        for y in range(0, height + 900, 900):
            await page.evaluate(f"window.scrollTo(0, {y})")
            await page.wait_for_timeout(120)
        await page.wait_for_timeout(400)
        await page.evaluate("document.fonts.ready")
        data = await page.evaluate(COLLECT_JS)
        data["fonts"] = await page.evaluate(FONT_JS)
        await browser.close()
    return data


def fetch(url, limit=6_000_000):
    # Un navigateur est annonce : plusieurs serveurs refusent un agent inconnu
    # par 403, ce qui ferait signaler comme mort un lien parfaitement valide.
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; check-release/1.0)",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.status, response.read(limit)


def check_spelling(text, market):
    """Signale l'orthographe qui n'est pas celle du marché visé."""
    found = []
    if market != "us":
        return found
    for pattern, expected in BRITISH.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            word = match.group(0)
            if expected.startswith("graphie") and word.lower() in ISE_EXCEPTIONS:
                continue
            found.append((word, expected))
    # Une seule ligne par mot fautif, pas une par occurrence.
    seen, unique = set(), []
    for word, expected in found:
        key = word.lower()
        if key not in seen:
            seen.add(key)
            unique.append((word, expected))
    return unique


def check_currency(text, market):
    """Une devise qui n'est pas celle du marche vise est une coquille de fond."""
    interdites = CURRENCY.get(market, ())
    trouve = []
    for mot in interdites:
        motif = rf"\b{re.escape(mot)}\b" if mot.isalpha() else re.escape(mot)
        m = re.search(motif, text, re.IGNORECASE)
        if m:
            phrase = text[max(0, m.start() - 45):m.start() + 55]
            trouve.append((mot, " ".join(phrase.split())))
    return trouve


def check_units(text, market):
    """Sur un marché impérial, une mesure métrique nue ne dit rien au lecteur."""
    if market != "us":
        return []
    problems = []
    for sentence in re.split(r"(?<=[.!?\n])\s+", text):
        if METRIC_RE.search(sentence) and not IMPERIAL_RE.search(sentence):
            problems.append(" ".join(sentence.split())[:110])
    return problems[:8]


def check_claims(text, pairs):
    """Deux affirmations opposées sur la même page : l'une des deux est fausse."""
    flat = " ".join(text.split())
    clashes = []
    for first, second in pairs:
        a = re.search(first, flat, re.IGNORECASE)
        b = re.search(second, flat, re.IGNORECASE)
        if a and b:
            clashes.append((a.group(0)[:70], b.group(0)[:70]))
    return clashes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="URL du site rendu (preview local ou production)")
    ap.add_argument("--dist", help="Dossier du build, pour vérifier la page 404")
    ap.add_argument("--market", default="", help="Marché visé : us, fr, uk… (us active l'orthographe américaine)")
    ap.add_argument("--claims", help="JSON de couples d'affirmations contradictoires à ajouter")
    ap.add_argument("--out", help="Où écrire le rapport JSON")
    args = ap.parse_args()

    try:
        data = asyncio.run(collect(args.url))
    except Exception as exc:
        sys.exit(f"Chargement impossible : {str(exc).splitlines()[0]}")

    errors, warnings = [], []

    # --- La police déclarée s'applique-t-elle vraiment ? ---------------------
    fonts = data.get("fonts") or {}
    manquants = fonts.get("missing") or []
    testes = fonts.get("tested") or 0
    if testes and manquants:
        part = len(manquants) / testes
        apercu = "".join(manquants[:24])
        famille = fonts.get("family") or "?"
        if part > 0.3:
            errors.append(
                f"La police « {famille} » ne couvre que {testes - len(manquants)} des {testes} "
                f"caractères de la page : le texte s'affiche en police système et l'identité "
                f"typographique n'existe pas. Presque toujours le mauvais sous-ensemble "
                f"téléchargé chez le fondeur (vietnamien, cyrillique, grec au lieu de latin).")
        else:
            warnings.append(
                f"La police « {famille} » ne couvre pas {len(manquants)} caractère(s) de la "
                f"page : {apercu}. Ils sortent dans une autre fonte, visible surtout sur Safari.")

    # --- Les liens : le defaut qui ne se voit pas et qui coupe la vente ------
    # Un catalogue externe qui tombe n'abime pas l'apparence de la page. Elle
    # reste belle, et elle ne vend plus rien. Personne ne s'en apercoit avant
    # qu'un client se plaigne.
    origine = urlparse(args.url).hostname
    vus = set()
    for lien in (data.get("links") or []):
        href = lien["href"].split("#")[0]
        if href in vus:
            continue
        vus.add(href)
        interne = urlparse(href).hostname == origine

        cible = "interne" if interne else "externe"
        try:
            status, _ = fetch(href, limit=2048)
        except urllib.error.HTTPError as e:
            # urllib leve sur 4xx et 5xx : sans ce cas, tout finirait en
            # « HTTPError », et un constat qui ne dit pas 404 ne sert a rien.
            status = e.code
        except Exception as exc:
            # Un lien interne injoignable est notre faute. Un lien externe qui
            # ne repond pas peut etre un incident passager chez un tiers : on
            # le signale sans bloquer une livraison pour autant.
            (errors if interne else warnings).append(
                f"Lien {cible} injoignable : {href} "
                f"(« {lien['texte']} », {type(exc).__name__}).")
            continue

        if status >= 400:
            (errors if interne else warnings).append(
                f"Lien {cible} mort ({status}) : {href} (« {lien['texte']} »).")

    # --- Indexation : ce que les robots viennent chercher --------------------
    for nom, role in (("robots.txt", "les robots ne savent pas ce qu'ils peuvent lire"),
                      ("sitemap.xml", "aucune liste d'URL n'est offerte a l'indexation")):
        cible = urljoin(args.url, "/" + nom)
        try:
            status, blob = fetch(cible)
            if status != 200:
                warnings.append(f"Pas de {nom} ({status}) : {role}.")
            elif nom == "robots.txt" and b"sitemap" not in blob.lower():
                warnings.append("robots.txt ne declare pas de Sitemap : "
                                "la ligne « Sitemap: » economise une decouverte a Google.")
        except Exception:
            warnings.append(f"Pas de {nom} : {role}.")

    # --- Un schema FAQ doit correspondre au texte visible --------------------
    # Google exige que chaque question et chaque reponse balisees apparaissent
    # sur la page. Un schema copie a la main derive des que le texte change, et
    # l'ecart ne se voit nulle part : le resultat enrichi disparait, sans motif.
    page = " ".join((data.get("allText") or "").split())
    for brut in data.get("jsonLd") or []:
        try:
            bloc = json.loads(brut)
        except Exception:
            errors.append("Un bloc de donnees structurees n'est pas du JSON valide : "
                          "Google l'ignore entierement.")
            continue
        for noeud in bloc if isinstance(bloc, list) else [bloc]:
            if not isinstance(noeud, dict) or noeud.get("@type") != "FAQPage":
                continue
            for q in noeud.get("mainEntity") or []:
                nom_q = " ".join(str(q.get("name", "")).split())
                rep = q.get("acceptedAnswer") or {}
                txt = " ".join(str(rep.get("text", "")).split())
                if nom_q and nom_q not in page:
                    errors.append(f"Question balisee absente de la page : « {nom_q[:70]} ». "
                                  "Le schema a derive du contenu.")
                if txt and txt[:60] not in page:
                    errors.append(f"Reponse balisee absente de la page, sous « {nom_q[:50]} ». "
                                  "Le schema a derive du contenu.")

    # --- Identité dans l'onglet ---------------------------------------------
    if not data["icons"]:
        errors.append("Aucune favicon déclarée : l'onglet affiche une page blanche générique.")
    else:
        target = urljoin(args.url, data["icons"][0])
        try:
            status, _ = fetch(target)
            if status != 200:
                errors.append(f"Favicon déclarée mais non servie ({status}) : {target}")
        except Exception as exc:
            errors.append(f"Favicon injoignable : {target} ({type(exc).__name__})")
    if not data["appleIcon"]:
        warnings.append("Pas d'apple-touch-icon : l'icône sera floue sur l'écran d'accueil d'un iPhone.")

    # --- Lien partagé --------------------------------------------------------
    og_image = data["ogImage"]
    if not og_image:
        errors.append("Aucune image de partage (og:image) : un lien partagé arrive nu.")
    elif not og_image.startswith(("http://", "https://")):
        errors.append(f"og:image en chemin relatif ({og_image}) : WhatsApp, LinkedIn et Facebook "
                      "exigent une URL absolue, sinon aucune vignette n'apparaît.")
    else:
        # L'og:image est absolu : il vise le domaine de production, qui n'est pas
        # toujours joignable depuis la machine qui contrôle (filtrage d'entreprise,
        # interception TLS, domaine tout juste enregistré). Un échec réseau ne dit
        # rien sur le fichier ; un 404 ou de mauvaises dimensions, si. On rejoue
        # donc le même chemin sur l'URL contrôlée avant de conclure.
        blob, source = None, ""
        try:
            status, blob = fetch(og_image)
            if status != 200:
                errors.append(f"Image de partage non servie ({status}) : {og_image}")
                blob = None
            source = "en ligne"
        except Exception as exc:
            local = urljoin(args.url, urlparse(og_image).path)
            try:
                status, blob = fetch(local)
                if status != 200:
                    raise RuntimeError(status)
                source = "dans le build"
                warnings.append(
                    f"Image de partage injoignable depuis cette machine ({type(exc).__name__}) : "
                    f"{og_image}. Le fichier est bien servi par le build ({local}) et ses "
                    "dimensions sont vérifiées, mais l'adresse publique reste à confirmer "
                    "depuis un réseau non filtré.")
            except Exception:
                blob = None
                errors.append(f"Image de partage injoignable : {og_image} ({type(exc).__name__}) "
                              f"et absente du build à {local}.")

        if blob is not None and data["ogImageWidth"] and data["ogImageHeight"]:
            try:
                from PIL import Image
                real = Image.open(BytesIO(blob)).size
                declared = (int(data["ogImageWidth"]), int(data["ogImageHeight"]))
                if real != declared:
                    errors.append(f"Dimensions de l'image de partage fausses ({source}) : déclarées "
                                  f"{declared[0]}x{declared[1]}, réelles {real[0]}x{real[1]}.")
            except ImportError:
                warnings.append("Pillow absent : dimensions de l'image de partage non vérifiées.")

    for field, label in (("ogTitle", "og:title"), ("ogDescription", "og:description"), ("ogUrl", "og:url")):
        if not data[field]:
            warnings.append(f"{label} absent : l'aperçu du lien sera incomplet.")

    # --- Recherche -----------------------------------------------------------
    if not data["canonical"]:
        warnings.append("Pas d'adresse canonique : le moteur choisira lui-même laquelle indexer.")
    if not data["description"]:
        errors.append("Pas de méta description : le moteur composera lui-même le résumé.")
    title = data["title"].strip()
    if not title:
        errors.append("Titre de page vide.")
    elif len(title) > 70:
        warnings.append(f"Titre de {len(title)} caractères : il sera coupé dans les résultats.")
    if not data["lang"]:
        errors.append("Attribut lang absent sur <html>.")

    # --- Ce qu'une maison sérieuse affiche toujours --------------------------
    footer = (data["footerText"] or "") + " " + data["text"][-1500:]
    if not re.search(r"©|\(c\)\s?\d{4}|all rights reserved|tous droits réservés", footer, re.IGNORECASE):
        errors.append("Aucune mention légale en pied de page (copyright ou droits réservés).")

    # --- Page 404 ------------------------------------------------------------
    if args.dist:
        if not (Path(args.dist) / "404.html").exists():
            errors.append(f"Pas de {args.dist}/404.html : une URL fausse tombera sur la page "
                          "d'erreur de l'hébergeur, pas sur la tienne.")

    # --- Marché --------------------------------------------------------------
    for mot, phrase in check_currency(data["text"], args.market.lower()):
        errors.append(f"Devise hors marche : « {mot} » sur un marche {args.market}. "
                      f"Contexte : ...{phrase}...")

    for word, expected in check_spelling(data["text"], args.market.lower()):
        errors.append(f"Orthographe hors marché : « {word} » → {expected}.")
    for sentence in check_units(data["text"], args.market.lower()):
        warnings.append(f"Mesure métrique sans équivalent impérial : « {sentence} »")

    # --- Contradictions ------------------------------------------------------
    pairs = list(DEFAULT_CLAIMS)
    if args.claims:
        pairs += json.loads(Path(args.claims).read_text(encoding="utf-8"))
    for first, second in check_claims(data["text"], pairs):
        errors.append(f"Contradiction dans la page : « {first} » et « {second} » "
                      "ne peuvent pas être vraies ensemble.")

    report = {"url": args.url, "market": args.market, "errors": errors, "warnings": warnings,
              "passed": not errors}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for item in errors:
        print(f"❌ {item}")
    for item in warnings:
        print(f"⚠ {item}")
    print(f"\n{len(errors)} bloquant(s), {len(warnings)} remarque(s).")
    print("RÉSULTAT :", "OK" if not errors else "LIVRAISON À CORRIGER")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
