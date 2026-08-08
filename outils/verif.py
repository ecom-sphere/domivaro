# -*- coding: utf-8 -*-
"""COMPARE EN SHA-256 CE QUE VERCEL SERT AVEC LE DEPOT LOCAL.

Incident du 07/08/2026 : 9 envois ont produit 9 constructions Vercel
concurrentes, l alias de production a atterri sur une version anterieure, et
les 108 pages repondaient 200. Un code 200 ne prouve rien. Seule la comparaison
des octets le prouve.

   python3 outils/verif.py                  toutes les pages du sitemap local
   python3 outils/verif.py les-prix/index.html es/precios/index.html

README.md et vercel.json ne sont pas servis, c est normal, ils sont ignores.
Sortie 0 si tout concorde, 1 sinon.
"""
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://domivaro.speed-ecom.eu"
NON_SERVIS = {"README.md", "vercel.json", "garde.py", "garde_local.py"}


def sha(octets):
    return hashlib.sha256(octets).hexdigest()


def url_depuis_chemin(rel):
    """index.html -> /   les-prix/index.html -> /les-prix/"""
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def tous_les_chemins():
    chemins = []
    for dossier, _, noms in os.walk(RACINE):
        if "/.git" in dossier or "/outils" in dossier:
            continue
        for nom in sorted(noms):
            rel = os.path.relpath(os.path.join(dossier, nom), RACINE)
            if rel in NON_SERVIS or rel.startswith("outils/"):
                continue
            chemins.append(rel)
    return sorted(chemins)


def main():
    demandes = [a for a in sys.argv[1:] if not a.startswith("-")]
    chemins = demandes or tous_les_chemins()

    ecarts, absents, ok = [], [], 0
    for rel in chemins:
        local = os.path.join(RACINE, rel)
        if not os.path.exists(local):
            absents.append(f"{rel} : absent en local")
            continue
        octets_locaux = open(local, "rb").read()
        url = BASE + url_depuis_chemin(rel) + f"?v={int(time.time())}"
        try:
            octets_servis = urllib.request.urlopen(url, timeout=45).read()
        except urllib.error.HTTPError as e:
            absents.append(f"{rel} : HTTP {e.code} sur {url_depuis_chemin(rel)}")
            continue
        except Exception as e:
            absents.append(f"{rel} : {type(e).__name__} sur {url_depuis_chemin(rel)}")
            continue

        a, b = sha(octets_locaux), sha(octets_servis)
        if a == b:
            ok += 1
        else:
            ecarts.append(
                f"{rel}\n    local  {a[:16]}  {len(octets_locaux)} octets"
                f"\n    servi  {b[:16]}  {len(octets_servis)} octets")

    print(f"\n{ok} fichier(s) identiques au dépôt sur {len(chemins)} compares.")
    if absents:
        print(f"\n{len(absents)} non lisible(s) :")
        for m in absents:
            print("  " + m)
    if ecarts:
        print(f"\n{len(ecarts)} ECART(S). Vercel sert autre chose que le dépôt :")
        for m in ecarts:
            print("  " + m)
        print("\nNe rien annoncer. Attendre la fin des constructions, puis relancer.")
        return 1
    if absents:
        return 1
    print("Tout concorde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
