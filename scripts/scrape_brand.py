#!/usr/bin/env python3
"""Extrait un dossier de marque brut depuis une URL : textes, couleurs CSS, polices, logo,
images, liens sociaux, et fiche produit complète si c'est une boutique Shopify.

Ne remplace pas l'œil : combine sa sortie avec une capture d'écran (Playwright MCP ou autre)
avant de décider la direction artistique. Bibliothèque standard uniquement.

Usage :
  python3 scrape_brand.py https://exemple.com [--download studio/assets/raw] [--catalog] [--out brand.json]

  --download  télécharge og:image, logo et images produit (pour extract_palette.py)
  --catalog   si boutique Shopify, récupère aussi les 12 premiers produits publics
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
SOCIAL = ("instagram.com", "tiktok.com", "facebook.com", "x.com", "twitter.com", "youtube.com",
          "linkedin.com", "pinterest.", "wa.me", "whatsapp.com", "snapchat.com")
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "initial", "cursive",
                 "-apple-system", "blinkmacsystemfont", "ui-sans-serif", "ui-serif", "ui-monospace",
                 "arial", "helvetica", "helvetica neue", "segoe ui", "roboto", "emoji", "var"}


def fetch(url, limit=3_000_000):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=20) as resp:
        return resp.read(limit), resp.headers.get_content_charset() or "utf-8", resp.geturl()


def fetch_text(url):
    body, charset, final = fetch(url)
    return body.decode(charset, errors="replace"), final


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.links, self.stylesheets, self.images, self.anchors = {}, [], [], [], []
        self.headings, self.buttons, self.inline_css = [], [], []
        self.title = ""
        self._stack = []
        self._text = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content"):
                self.meta[key.lower()] = a["content"]
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if "stylesheet" in rel and a.get("href"):
                self.stylesheets.append(a["href"])
            if "icon" in rel and a.get("href"):
                self.links.append(("icon", a["href"], a.get("sizes", "")))
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or (a.get("srcset", "").split(" ")[0])
            if src:
                self.images.append({"src": src, "alt": a.get("alt", ""), "hint": (a.get("class", "") + a.get("id", "")).lower()})
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
        if tag in ("title", "h1", "h2", "h3", "button", "style") or (tag == "a" and "btn" in a.get("class", "")):
            self._stack.append(tag)
            self._text = []

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
            text = " ".join("".join(self._text).split())
            if tag == "title":
                self.title = text
            elif tag in ("h1", "h2", "h3") and text:
                self.headings.append((tag, text[:160]))
            elif tag in ("button", "a") and text and len(text) < 40:
                self.buttons.append(text)
            elif tag == "style":
                self.inline_css.append("".join(self._text))
            self._text = []

    def handle_data(self, data):
        if self._stack:
            self._text.append(data)


def css_signals(css_texts):
    hexes = Counter()
    fonts = Counter()
    custom_props = {}
    for css in css_texts:
        for m in re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
            h = m.lower()
            if len(h) == 4:
                h = "#" + "".join(c * 2 for c in h[1:])
            hexes[h] += 1
        for fam in re.findall(r"font-family\s*:\s*([^;}{]+)", css):
            first = fam.split(",")[0].strip().strip("'\"").lower()
            if first and first not in GENERIC_FONTS and not first.startswith("var("):
                fonts[first] += 1
        for fam in re.findall(r"@font-face\s*{[^}]*font-family\s*:\s*['\"]?([^;'\"]+)", css):
            fonts[fam.strip().lower()] += 3
        for name, val in re.findall(r"(--[\w-]*(?:color|colour|brand|primary|accent|bg|background)[\w-]*)\s*:\s*([^;}{]+)", css, re.I):
            val = val.strip()
            if name.startswith("--tw-") or re.match(r"^--color-[a-z]+-\d{2,3}$", name) or not re.match(r"(#|rgb|hsl|oklch|oklab|color\()", val, re.I):
                continue
            custom_props.setdefault(name, val)
    trivial = {"#ffffff", "#000000", "#fff", "#000"}
    return {
        "top_colors": [c for c, _ in hexes.most_common(14) if c not in trivial][:10],
        "fonts": [f for f, _ in fonts.most_common(6)],
        "color_custom_properties": dict(list(custom_props.items())[:15]),
    }


def shopify_product(url):
    parts = urlparse(url)
    path = parts.path.rstrip("/")
    if "/products/" not in path:
        return None
    json_url = urlunparse(parts._replace(path=path + ".json", query="", fragment=""))
    try:
        raw, _ = fetch_text(json_url)
        product = json.loads(raw)["product"]
    except Exception:
        return None
    body = re.sub(r"<[^>]+>", " ", product.get("body_html") or "")
    return {
        "title": product.get("title"),
        "vendor": product.get("vendor"),
        "type": product.get("product_type"),
        "tags": product.get("tags"),
        "description": " ".join(html.unescape(body).split())[:1500],
        "options": [{"name": o.get("name"), "values": o.get("values")} for o in product.get("options", [])],
        "variants": [{"title": v.get("title"), "price": v.get("price"), "compare_at_price": v.get("compare_at_price")}
                     for v in product.get("variants", [])[:30]],
        "images": [i.get("src") for i in product.get("images", [])],
    }


def shopify_catalog(url):
    parts = urlparse(url)
    try:
        raw, _ = fetch_text(urlunparse(parts._replace(path="/products.json", query="limit=12", fragment="")))
        items = json.loads(raw)["products"]
    except Exception:
        return None
    return [{"title": p.get("title"), "handle": p.get("handle"), "type": p.get("product_type"),
             "price": (p.get("variants") or [{}])[0].get("price"),
             "image": (p.get("images") or [{}])[0].get("src")} for p in items]


def download(urls, dest):
    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, u in enumerate(urls):
        try:
            body, _, final = fetch(u, limit=15_000_000)
        except Exception as exc:
            print(f"⚠ téléchargement impossible : {u} ({exc})", file=sys.stderr)
            continue
        ext = Path(urlparse(final).path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg"):
            ext = ".jpg"
        target = dest / f"{i:02d}{ext}"
        target.write_bytes(body)
        saved.append(str(target))
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--download")
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    try:
        page_html, final_url = fetch_text(args.url)
    except Exception as exc:
        sys.exit(f"Impossible de charger {args.url} : {exc}\n→ Utilise une capture Playwright ou demande des captures d'écran.")

    parser = PageParser()
    parser.feed(page_html)
    absolute = lambda u: urljoin(final_url, html.unescape(u))

    css_texts = list(parser.inline_css)
    for href in parser.stylesheets[:4]:
        try:
            css_texts.append(fetch_text(absolute(href))[0])
        except Exception:
            pass
    css = css_signals(css_texts)
    google_fonts = sorted({
        f.replace("+", " ") for href in parser.stylesheets if "fonts.googleapis.com" in href
        for f in re.findall(r"family=([^:&]+)", href)
    })

    logos = [absolute(i["src"]) for i in parser.images
             if "logo" in i["hint"] or "logo" in i["src"].lower() or "logo" in i["alt"].lower()][:3]
    icons = sorted(parser.links, key=lambda l: len(l[2]), reverse=True)
    is_shopify = "cdn.shopify.com" in page_html or "Shopify.shop" in page_html

    result = {
        "url": final_url,
        "platform": "shopify" if is_shopify else "unknown",
        "title": parser.title,
        "description": parser.meta.get("description") or parser.meta.get("og:description"),
        "site_name": parser.meta.get("og:site_name"),
        "og_image": absolute(parser.meta["og:image"]) if parser.meta.get("og:image") else None,
        "theme_color": parser.meta.get("theme-color"),
        "logo_candidates": logos,
        "icon": absolute(icons[0][1]) if icons else None,
        "headings": parser.headings[:20],
        "cta_texts": list(dict.fromkeys(parser.buttons))[:15],
        "social_links": sorted({absolute(a) for a in parser.anchors if any(s in a for s in SOCIAL)})[:10],
        "css_colors": css["top_colors"],
        "css_color_variables": css["color_custom_properties"],
        "fonts_detected": list(dict.fromkeys(google_fonts + css["fonts"])),
        "images_sample": list(dict.fromkeys(absolute(i["src"]) for i in parser.images if not i["src"].startswith("data:")))[:15],
    }

    if is_shopify:
        result["shopify_product"] = shopify_product(final_url)
        if args.catalog:
            result["shopify_catalog"] = shopify_catalog(final_url)

    if args.download:
        wanted = [u for u in [result["og_image"], *logos] if u]
        if result.get("shopify_product"):
            wanted += result["shopify_product"]["images"][:6]
        result["downloaded"] = download(list(dict.fromkeys(wanted)), Path(args.download))

    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
