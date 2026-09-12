#!/usr/bin/env python3
"""Vérifie que chaque chiffre affiché sur le site vient d'une source déclarée.

Deux contrôles :
1. TEXTE — tous les nombres visibles (texte rendu, attributs alt et aria-label) sont extraits
   et comparés à studio/facts.json. Un nombre absent des faits est signalé « non sourcé ».
2. VISUELS — les composants qui dessinent des données (grilles, barres, jauges, compteurs)
   déclarent leurs contrôles dans window.__FACT_CHECKS__ (voir src/lib/fact-checks.ts du template).
   Toute différence entre valeur attendue et valeur réellement rendue est une erreur.

Usage :
  python3 check_facts.py http://localhost:4173 --facts studio/facts.json [--out studio/review/facts-report.json]
  python3 check_facts.py dist/index.html --facts studio/facts.json      # fichier local

Code de sortie 1 s'il reste un nombre non sourcé ou un contrôle visuel en échec.
Dépendances : pip install playwright && python -m playwright install chromium
"""
import argparse
import ast
import asyncio
import json
import operator
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

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit("Playwright manquant : pip install playwright && python -m playwright install chromium")

NUMBER_RE = re.compile(
    r"(?<![\w.,])"
    # groupes de milliers séparés par espace/point (fr) ou virgule (en), puis décimales
    r"(\d{1,3}(?:[   .,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?![\d])"
)
# Sous ce nombre de caractères rendus, la page est considérée vide et le contrôle
# échoue. Sans ce garde-fou, une page blanche ne contient aucun nombre, donc aucun
# écart, donc « RÉSULTAT : OK » — le pire des faux positifs.
MIN_BODY_CHARS = 200

# Ordinaux (1er, 2e, 3ème, 21st…) : ce ne sont pas des quantités à sourcer
ORDINAL_RE = re.compile(r"\b\d+\s?(?:er|re|ère|e|ème|nd|nde|st|th|rd)\b", re.IGNORECASE)

COLLECT_JS = """
() => {
  const texts = [document.body.innerText];
  document.querySelectorAll('[alt], [aria-label], [title]').forEach(el => {
    ['alt', 'aria-label', 'title'].forEach(attr => { const v = el.getAttribute(attr); if (v) texts.push(v); });
  });
  document.querySelectorAll('meta[name="description"], meta[property^="og:"]').forEach(m => texts.push(m.content || ''));
  texts.push(document.title);
  return {
    texts,
    checks: window.__FACT_CHECKS__ || [],
    bodyLength: (document.body.innerText || '').trim().length,
  };
}
"""

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.USub: operator.neg, ast.Pow: operator.pow}


def safe_eval(formula, values):
    """Évalue une formule arithmétique simple dont les variables sont des identifiants de faits."""
    expr = re.sub(r"[A-Za-z_][\w.]*", lambda m: f"__v[{m.group(0)!r}]", formula)
    tree = ast.parse(expr, mode="eval")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.operand))
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "__v"
                and isinstance(node.slice, ast.Constant)):
            key = node.slice.value
            if key not in values:
                raise KeyError(f"fait inconnu dans la formule : {key}")
            return values[key]
        raise ValueError(f"expression non autorisée : {formula}")

    return walk(tree)


def parse_number(token):
    """Lit les deux conventions : « 30 000,5 » / « 30.000,5 » (fr) et « 30,000.5 » (en)."""
    t = token.replace(" ", " ").replace(" ", " ")
    # anglais : virgules pour les milliers, point décimal
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):
        t = t.replace(",", "")
    # français : espaces ou points pour les milliers, virgule décimale
    elif re.fullmatch(r"\d{1,3}(?:[ .]\d{3})+(?:,\d+)?", t):
        t = t.replace(" ", "").replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def load_facts(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    values = {}
    for fact in data.get("facts", []):
        if "id" not in fact or "value" not in fact:
            sys.exit(f"Fait invalide (id et value obligatoires) : {fact}")
        if not fact.get("source"):
            print(f"⚠ Fait sans source : {fact['id']}", file=sys.stderr)
        values[fact["id"]] = float(fact["value"])
    for derived in data.get("derived", []):
        values[derived["id"]] = float(safe_eval(derived["formula"], values))

    allowed = set(values.values())
    for fact in data.get("facts", []) + data.get("derived", []):
        for alias in fact.get("aliases", []):
            allowed.add(float(alias))
    ignore = [re.compile(p) for p in data.get("ignore_patterns", [])]
    allowed.update(float(n) for n in data.get("allowed_numbers", []))
    return values, allowed, ignore


async def collect(target):
    url = target
    if not re.match(r"^https?://", target):
        url = Path(target).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(url, wait_until="networkidle")
        # Parcourt la page pour déclencher les composants chargés au défilement
        height = await page.evaluate("document.documentElement.scrollHeight")
        for y in range(0, height + 900, 900):
            await page.evaluate(f"window.scrollTo(0, {y})")
            await page.wait_for_timeout(120)
        await page.wait_for_timeout(500)
        result = await page.evaluate(COLLECT_JS)
        await browser.close()
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="URL ou fichier HTML local")
    ap.add_argument("--facts", default="studio/facts.json")
    ap.add_argument("--out")
    args = ap.parse_args()

    if not Path(args.facts).exists():
        sys.exit(f"{args.facts} introuvable : crée d'abord le registre des faits (voir references/facts.md).")
    values, allowed, ignore = load_facts(args.facts)

    try:
        data = asyncio.run(collect(args.target))
    except Exception as exc:
        sys.exit(f"Chargement impossible : {str(exc).splitlines()[0]}")

    blank = data.get("bodyLength", 0) < MIN_BODY_CHARS

    unsourced = {}
    for text in data["texts"]:
        clean = ORDINAL_RE.sub(" ", text)
        for pattern in ignore:
            clean = pattern.sub(" ", clean)
        for match in NUMBER_RE.finditer(clean):
            number = parse_number(match.group(1))
            if number is None or any(abs(number - a) < 1e-9 for a in allowed):
                continue
            start = max(0, match.start() - 40)
            context = " ".join(clean[start:match.end() + 40].split())
            unsourced.setdefault(match.group(1), context)

    failed_checks = []
    for check in data["checks"]:
        expected, actual = check.get("expected"), check.get("actual")
        fact_id = check.get("fact")
        if fact_id and fact_id in values and expected is not None and abs(float(expected) - values[fact_id]) > 1e-9:
            failed_checks.append({**check, "problem": f"attendu {expected} mais le fait {fact_id} vaut {values[fact_id]}"})
        elif expected is None or actual is None or abs(float(expected) - float(actual)) > 1e-9:
            failed_checks.append({**check, "problem": f"attendu {expected}, rendu {actual}"})

    report = {
        "target": args.target,
        "page_text_length": data.get("bodyLength", 0),
        "blank_page": blank,
        "unsourced_numbers": [{"number": n, "context": c} for n, c in unsourced.items()],
        "visual_checks": len(data["checks"]),
        "failed_visual_checks": failed_checks,
        "passed": not blank and not unsourced and not failed_checks,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if blank:
        print(f"❌ Page vide ou presque : {data.get('bodyLength', 0)} caractère(s) rendus "
              f"(seuil {MIN_BODY_CHARS}).")
        print("   Cause la plus fréquente : le build est servi à la racine alors qu'il attend "
              "son chemin de base. Utilise « npm run preview » et l'URL complète, pas un "
              "serveur statique sur dist/.")
    for item in report["unsourced_numbers"]:
        print(f"❌ Nombre non sourcé « {item['number']} » : …{item['context']}…")
    for check in failed_checks:
        print(f"❌ Visuel « {check.get('name', '?')} » : {check['problem']}")
    if not data["checks"]:
        print("ℹ Aucun contrôle visuel déclaré (window.__FACT_CHECKS__ vide). "
              "Normal s'il n'y a ni graphique ni compteur ; sinon, les déclarer.")
    print(f"{len(data['checks'])} contrôle(s) visuel(s), {len(unsourced)} nombre(s) non sourcé(s).")
    print("RÉSULTAT :", "OK" if report["passed"] else "CHIFFRES À CORRIGER")
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
