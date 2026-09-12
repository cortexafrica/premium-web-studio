#!/usr/bin/env python3
"""Contrôle de sécurité : ce qu'un attaquant regarde en premier.

Aucun site n'est « impossible à pirater », et un outil qui le promettrait
serait dangereux : on cesse de surveiller ce qu'on croit invulnérable. Ce
script fait la seule chose utile — chercher, avant livraison, les erreurs qui
ouvrent vraiment une porte sur ce type d'architecture : un site statique, des
fonctions serveur qui détiennent les clés, un domaine.

Il vérifie :
  - aucun secret dans le build servi, ni dans le dépôt, ni dans son historique ;
  - les en-têtes de sécurité réellement servis par l'hébergeur ;
  - les fichiers qui ne devraient jamais être accessibles (.env, .git, cartes
    de sources) ;
  - les fonctions serveur : en-tête d'origine EXIGÉ et non seulement vérifié,
    refus d'une origine étrangère, refus d'une requête sans origine ;
  - le domaine : SPF, DMARC, CAA, DNSSEC ;
  - les dépendances, via npm audit.

Usage :
  python3 check_security.py https://exemple.com --dist site/dist --repo site \\
          --functions https://xxx.supabase.co/functions/v1/quote,.../ask

Code de sortie 1 dès qu'un point bloquant échoue.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import urllib.parse
from urllib.parse import urljoin, urlparse

# Une console Windows repond souvent en cp1252 : le premier caractere non
# latin-1 affiche interrompt le script et le controle ne rend aucun verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# --- Secrets : les formes qui coutent de l'argent quand elles fuient ---------
# Chaque motif vise un prefixe propre a un fournisseur. On evite volontairement
# les regles generiques du type « chaine de 32 caracteres » : elles noient le
# rapport sous des faux positifs et on finit par ne plus le lire.
SECRETS = {
    "clé OpenAI": r"\bsk-[A-Za-z0-9]{20,}",
    "clé Anthropic": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "clé DeepSeek": r"\bsk-[a-f0-9]{32}\b",
    "clé Resend": r"\bre_[A-Za-z0-9_]{16,}",
    "clé Stripe secrète": r"\bsk_(live|test)_[A-Za-z0-9]{16,}",
    "jeton GitHub": r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "clé AWS": r"\bAKIA[0-9A-Z]{16}\b",
    "clé de service Supabase": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    "clé Google": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "URL avec mot de passe": r"\b[a-z+]+://[^/\s:@]+:[^/\s:@]+@",
}

# Les en-tetes qui changent quelque chose, et ce qu'ils empechent.
HEADERS = {
    "strict-transport-security":
        ("bloquant", "sans HSTS, une première visite en clair peut être interceptée"),
    "x-content-type-options":
        ("remarque", "sans nosniff, un fichier peut être exécuté comme un autre type"),
    "content-security-policy":
        ("remarque", "sans CSP, un script injecté s'exécute sans contrainte"),
    "referrer-policy":
        ("remarque", "sans elle, l'URL complète fuit vers les sites tiers"),
    "x-frame-options":
        ("remarque", "sans elle, la page peut être encadrée pour piéger un clic"),
}

# Ce qui ne doit jamais repondre 200 sur un site livre.
JAMAIS_SERVI = [
    (".env", "les variables d'environnement, clés comprises"),
    (".git/config", "tout l'historique du dépôt devient téléchargeable"),
    (".git/HEAD", "tout l'historique du dépôt devient téléchargeable"),
    ("package.json", "la liste des dépendances et leurs versions exactes"),
    (".DS_Store", "l'arborescence des fichiers du dossier"),
    ("backup.zip", "une sauvegarde laissée en ligne"),
]


def fetch(url, methode="GET", corps=None, entetes=None, timeout=30):
    """Renvoie (code, en-têtes, contenu). Ne lève pas sur un code d'erreur."""
    req = urllib.request.Request(
        url, method=methode,
        data=corps.encode() if corps else None,
        headers={"User-Agent": "check-security/1.0", **(entetes or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(200_000)
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read(200_000)
    except Exception as exc:
        return None, {}, str(exc).encode()


def dns_txt(nom):
    """Interroge un enregistrement TXT sans dépendance externe."""
    try:
        sortie = subprocess.run(["nslookup", "-type=TXT", nom, "8.8.8.8"],
                                capture_output=True, text=True, errors="replace",
                                timeout=30).stdout
        return re.findall(r'"([^"]*)"', sortie)
    except Exception:
        return []


def dns_type(nom, type_):
    try:
        return subprocess.run(["nslookup", f"-type={type_}", nom, "8.8.8.8"],
                              capture_output=True, text=True, errors="replace",
                              timeout=30).stdout
    except Exception:
        return ""


# Deux fournisseurs : une panne de l'un ne doit pas faire conclure a une absence.
RESOLVEURS = (
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query",
)


def dns_doh(nom, type_):
    """Interroge un type quelconque, sans dependre des outils du systeme.

    Renvoie (enregistrements, interroge). « interroge » vaut False quand aucun
    resolveur n'a repondu : l'appelant doit alors dire qu'il n'a PAS PU
    verifier, et surtout pas que l'enregistrement est absent.

    nslookup ne suffisait pas : celui de Windows ignore les types CAA et DNSKEY
    et repond « unknown query type ». Le controle lisait cette absence de
    reponse comme une absence d'enregistrement, et emettait sa remarque quoi
    qu'il arrive.
    """
    for base in RESOLVEURS:
        url = f"{base}?name={urllib.parse.quote(nom)}&type={type_}"
        requete = urllib.request.Request(url, headers={
            "accept": "application/dns-json",
            "User-Agent": "check-security/1.0",
        })
        try:
            with urllib.request.urlopen(requete, timeout=25) as reponse:
                data = json.loads(reponse.read(200_000).decode("utf-8", "replace"))
        except Exception:
            continue
        if data.get("Status") not in (0, 3):      # 3 = le nom n'existe pas
            continue
        return [r.get("data", "") for r in (data.get("Answer") or [])], True
    return [], False


# --- Les contrôles -----------------------------------------------------------

def secrets_dans(chemin: Path, bloquants, remarques):
    """Cherche des clés dans un dossier. C'est le contrôle qui compte le plus :
    une clé qui fuit est exploitée en quelques minutes par des robots qui
    surveillent les dépôts publics en continu."""
    if not chemin or not chemin.exists():
        return
    for f in chemin.rglob("*"):
        if not f.is_file() or ".git" in f.parts or "node_modules" in f.parts:
            continue
        if f.stat().st_size > 4_000_000:
            continue
        try:
            texte = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for nom, motif in SECRETS.items():
            m = re.search(motif, texte)
            if m:
                bloquants.append(
                    f"{nom} trouvée dans {f.relative_to(chemin)} : « {m.group(0)[:14]}… ». "
                    "À révoquer chez le fournisseur AVANT toute autre action, "
                    "puis à sortir du fichier.")


def secrets_dans_historique(repo: Path, bloquants, remarques):
    """Un secret retiré d'un fichier reste dans l'historique, et un dépôt public
    est moissonné en permanence. Le retirer du dernier commit ne suffit pas."""
    if not repo or not (repo / ".git").exists():
        return
    try:
        sortie = subprocess.run(
            ["git", "-C", str(repo), "log", "-p", "--all", "-S", "sk-", "--oneline"],
            capture_output=True, text=True, errors="replace", timeout=90).stdout
    except Exception:
        remarques.append("historique git non lisible : contrôle des secrets passés ignoré.")
        return
    for nom, motif in SECRETS.items():
        if re.search(motif, sortie):
            bloquants.append(
                f"{nom} présente dans l'HISTORIQUE git. La retirer du fichier ne suffit "
                "pas : elle reste téléchargeable. Révoquer la clé, c'est la seule "
                "réponse qui ferme vraiment la porte.")


# Hebergements statiques qui ne permettent pas de definir d'en-tetes. Sur
# ceux-la, l'absence n'est pas une negligence : c'est une propriete de la
# plateforme, et le remede est de placer un intermediaire devant.
SANS_ENTETES = ("github.com", "github pages")


def fetch_tenace(url, methode="GET", corps=None, entetes_http=None, essais=3):
    """Comme fetch(), mais ne conclut pas a l'injoignable sur un seul echec.

    Renvoie (code, en-tetes, contenu, cause). « cause » est None des qu'une
    reponse HTTP est revenue, quel que soit son code.

    On ne rejoue que l'echec de niveau reseau — code None, donc rien n'est
    parvenu au serveur. Rejouer une requete effectivement recue risquerait de
    la declencher deux fois.
    """
    cause = None
    for essai in range(essais):
        code, h, contenu = fetch(url, methode, corps, entetes_http)
        if code is not None:
            return code, h, contenu, None
        cause = (contenu or b"").decode("utf-8", "replace") or "cause inconnue"
        if essai < essais - 1:
            time.sleep(1 + essai)      # 1 s, puis 2 s : de quoi passer un a-coup
    return None, {}, b"", cause


def entetes(url, bloquants, remarques):
    code, h, _, cause = fetch_tenace(url)
    if code is None:
        # La cause est dans le constat : « injoignable » ne dit pas si c'est le
        # DNS, le certificat, un delai depasse ou un refus, et le lecteur
        # refait alors l'enquete que le script venait de faire.
        bloquants.append(f"Site injoignable apres 3 tentatives : {url} ({cause})")
        return

    serveur = (h.get("server") or "").lower()
    bride = any(nom in serveur for nom in SANS_ENTETES)

    manquants = [nom for nom in HEADERS if nom not in h]
    if bride and manquants:
        remarques.append(
            f"Aucun en-tête de sécurité ({', '.join(manquants)}) : l'hébergement "
            f"« {h.get('server', '?')} » ne permet pas d'en définir. Ce n'est pas un "
            "oubli à corriger dans le code. Pour une vitrine, c'est acceptable et il "
            "faut le DIRE au client. Pour un site qui manipule des données, placer un "
            "intermédiaire devant (Cloudflare en offre gratuite) donne le contrôle des "
            "en-têtes, le HSTS et un filtrage du trafic. C'est un changement "
            "d'architecture : à proposer, pas à décider seul.")
    else:
        for nom in manquants:
            gravite, pourquoi = HEADERS[nom]
            (bloquants if gravite == "bloquant" else remarques).append(
                f"En-tête absent : {nom} — {pourquoi}.")

    if urlparse(url).scheme != "https":
        bloquants.append("Le site est servi en clair : tout transite en lisible.")


def fichiers_exposes(url, bloquants, remarques):
    for chemin, quoi in JAMAIS_SERVI:
        code, _, corps = fetch(urljoin(url, "/" + chemin))
        # Une page 404 personnalisee repond parfois 200 : on exige un contenu
        # qui ressemble vraiment au fichier cherche.
        if code == 200 and b"<!doctype html" not in corps[:200].lower():
            bloquants.append(f"/{chemin} est accessible : {quoi}.")
    code, _, corps = fetch(url)
    if code == 200 and re.search(rb"sourceMappingURL=.*\.map", corps):
        remarques.append("Une carte de sources est référencée : le code d'origine "
                         "devient lisible, commentaires compris.")


# Les noms de champs par lesquels un service raconte sa propre configuration.
# On ne cherche pas un secret — un secret en clair serait deja attrape par le
# controle des secrets — mais l'aveu qu'il y en a un, et qu'il est en place.
ETAT_SENSIBLE = (
    "key", "token", "secret", "credential", "apikey", "auth",
    "config", "env", "detected", "configured", "enabled", "ready",
    "debug", "version", "build", "commit",
)


def etat_divulgue(corps):
    """Champs de configuration trouves dans un corps JSON. Liste vide sinon.

    La valeur n'est recopiee que si elle est booleenne ou numerique : un rapport
    est un fichier, il se partage et se commit, et il ne doit jamais devenir
    l'endroit ou une valeur sensible finit par etre ecrite.
    """
    try:
        data = json.loads((corps or b"").decode("utf-8", "replace"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []

    trouves = []
    for champ, valeur in data.items():
        if not any(mot in champ.lower() for mot in ETAT_SENSIBLE):
            continue
        if isinstance(valeur, bool) or isinstance(valeur, (int, float)):
            trouves.append((champ, repr(valeur)))
        else:
            # Ni la valeur ni un extrait : seulement de quoi la reconnaitre.
            trouves.append((champ, f"une valeur de {len(str(valeur))} caractères"))
    return trouves


def fonctions(urls, bloquants, remarques):
    """Le point faible habituel de cette architecture : la fonction detient les
    cles, et c'est le controle d'origine qui decide qui peut la faire agir."""
    # Une charge qui echoue avant tout effet de bord : on sonde sans rien
    # declencher. Le champ « company » est le piege a robots de ces fonctions.
    sonde = json.dumps({"source": "chat", "email": "probe@example.invalid",
                        "question": "ping", "company": "probe"})
    for u in urls:
        nom = u.rstrip("/").split("/")[-1]

        code, _, _, cause = fetch_tenace(
            u, "POST", sonde, {"Content-Type": "application/json"})
        if code is None:
            remarques.append(f"Fonction « {nom} » injoignable apres 3 tentatives, "
                             f"contrôle impossible ({cause}).")
            continue
        if code not in (401, 403):
            bloquants.append(
                f"Fonction « {nom} » : une requête SANS en-tête Origin est acceptée "
                f"(code {code}). Un navigateur en envoie toujours un ; l'omettre est le "
                "fait d'un script. Exiger l'en-tête, ne pas seulement le vérifier "
                "quand il est présent — le piège classique est « if (origin && ... ) ».")

        code, _, _ = fetch(u, "POST", sonde, {
            "Content-Type": "application/json", "Origin": "https://attaquant.invalid"})
        if code not in (401, 403):
            bloquants.append(
                f"Fonction « {nom} » : une origine étrangère est acceptée (code {code}). "
                "N'importe quel site peut faire agir la fonction au nom de vos visiteurs.")

        code, _, corps = fetch(u, "GET")
        if code == 200:
            remarques.append(f"Fonction « {nom} » répond 200 en GET : cela confirme "
                             "à un inconnu que le point d'entrée existe et tourne. "
                             "Si rien ne l'exige (vérification de webhook, sonde de "
                             "santé), répondre 405 comme aux autres verbes.")
            for champ, valeur in etat_divulgue(corps):
                remarques.append(
                    f"Fonction « {nom} » divulgue son état de configuration en GET : "
                    f"le champ « {champ} » vaut {valeur}. C'est le premier "
                    "renseignement que cherche quelqu'un qui sonde un service.")


def domaine(hote, bloquants, remarques):
    txt = " ".join(dns_txt(hote))
    if "v=spf1" not in txt:
        remarques.append("Pas de SPF : n'importe qui peut écrire en se faisant passer "
                         "pour votre domaine, et ses messages passeront les filtres.")
    if "v=DMARC1" not in " ".join(dns_txt("_dmarc." + hote)):
        remarques.append("Pas de DMARC : rien n'indique aux serveurs destinataires quoi "
                         "faire d'un message usurpé. C'est l'enregistrement qui rend le "
                         "SPF utile.")
    caa, interroge = dns_doh(hote, "CAA")
    if not interroge:
        remarques.append("CAA : contrôle impossible, aucun résolveur n'a répondu. "
                         "Ce n'est pas la même chose qu'un enregistrement absent.")
    elif not caa:
        remarques.append("Pas d'enregistrement CAA : n'importe quelle autorité peut "
                         "émettre un certificat pour votre domaine.")
    elif not any(" issue " in f" {c} " or c.strip().startswith(("0 issue ", "128 issue "))
                 for c in caa):
        # RFC 8659 §4.3 : « Each issuewild Property MUST be ignored when
        # processing a request for an FQDN that is not a Wildcard Domain Name ».
        # Un jeu CAA sans propriete « issue » ne protege donc que les
        # certificats generiques, et laisse passer tous les autres.
        remarques.append(
            f"CAA présent mais sans propriété « issue » : {caa}. "
            "« issuewild » ne gouverne que les certificats génériques "
            "(*.domaine) ; pour un certificat ordinaire, n'importe quelle "
            "autorité reste autorisée. Remplacer l'étiquette par « issue ».")

    dnskey, interroge = dns_doh(hote, "DNSKEY")
    if not interroge:
        remarques.append("DNSSEC : contrôle impossible, aucun résolveur n'a répondu.")
    elif not dnskey:
        remarques.append("DNSSEC absent : une réponse DNS peut être falsifiée en chemin. "
                         "Un détournement de domaine annule toutes les autres protections.")


def dependances(repo: Path, bloquants, remarques):
    if not repo or not (repo / "package.json").exists():
        return
    try:
        sortie = subprocess.run(["npm", "audit", "--json", "--audit-level=high"],
                                cwd=repo, capture_output=True, text=True,
                                errors="replace", timeout=180, shell=True).stdout
        data = json.loads(sortie or "{}")
    except Exception:
        remarques.append("npm audit non exécutable : contrôle des dépendances ignoré.")
        return
    total = (data.get("metadata", {}).get("vulnerabilities", {}) or {})
    for gravite in ("critical", "high"):
        n = total.get(gravite, 0)
        if n:
            bloquants.append(f"{n} dépendance(s) de gravité « {gravite} » : "
                             "corriger avec npm audit fix avant livraison.")
    for gravite in ("moderate", "low"):
        n = total.get(gravite, 0)
        if n:
            remarques.append(f"{n} dépendance(s) de gravité « {gravite} ».")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="URL du site en ligne")
    ap.add_argument("--dist", help="Dossier du build servi")
    ap.add_argument("--repo", help="Racine du dépôt git")
    ap.add_argument("--functions", default="",
                    help="URLs des fonctions serveur, séparées par des virgules")
    ap.add_argument("--out", help="Dossier où écrire le rapport JSON")
    ap.add_argument("--offline", action="store_true",
                    help="Ne garder que ce qui se vérifie sans le site en ligne : "
                         "les secrets dans le build et dans l'historique du dépôt")
    args = ap.parse_args()

    bloquants, remarques = [], []

    print("secrets dans le build…")
    secrets_dans(Path(args.dist) if args.dist else None, bloquants, remarques)
    print("secrets dans le dépôt et son historique…")
    repo = Path(args.repo) if args.repo else None
    secrets_dans(repo, bloquants, remarques)
    secrets_dans_historique(repo, bloquants, remarques)
    if args.offline:
        print("mode hors ligne : en-têtes, fichiers servis, fonctions et domaine "
              "ne seront vérifiés que sur l'URL en ligne.")
    else:
        print("en-têtes de sécurité…")
        entetes(args.url, bloquants, remarques)
        print("fichiers qui ne devraient pas être servis…")
        fichiers_exposes(args.url, bloquants, remarques)
        if args.functions:
            print("fonctions serveur…")
            fonctions([u.strip() for u in args.functions.split(",") if u.strip()],
                      bloquants, remarques)
        print("domaine…")
        domaine(urlparse(args.url).hostname or "", bloquants, remarques)
    print("dépendances…")
    dependances(repo, bloquants, remarques)

    print()
    for b in bloquants:
        print(f"❌ {b}")
    for r in remarques:
        print(f"⚠ {r}")
    print(f"\n{len(bloquants)} bloquant(s), {len(remarques)} remarque(s).")

    if args.out:
        d = Path(args.out)
        d.mkdir(parents=True, exist_ok=True)
        (d / "security.json").write_text(
            json.dumps({"url": args.url, "errors": bloquants, "warnings": remarques},
                       ensure_ascii=False, indent=2), encoding="utf-8")

    print("RÉSULTAT :", "SÉCURITÉ À CORRIGER" if bloquants else "OK")
    print("\nRappel : ce script écarte les erreurs connues, il ne rend rien "
          "inviolable. Ce qu'il ne verra jamais : un mot de passe réutilisé, "
          "l'absence de double authentification, un accès laissé à un ancien "
          "prestataire. Ces trois-là causent plus d'intrusions que tout le reste.")
    sys.exit(1 if bloquants else 0)


if __name__ == "__main__":
    main()
