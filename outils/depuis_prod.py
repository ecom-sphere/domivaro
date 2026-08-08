# -*- coding: utf-8 -*-
"""Repart de la production avant d ecrire quoi que ce soit. A LANCER EN PREMIER
DANS CHAQUE LOT.

POURQUOI. Le 08/08/2026, l arbre local est retombe 3 fois, en silence, sur le
commit du lot 65, alors que la production etait au lot 84. Les 3 fois, un lot a
ete ecrit par-dessus des fichiers perimes ; les 3 fois, l envoi aurait annule
des corrections deja livrees. Le dernier cas aurait efface le reviewCount
corrige a 24, la comparaison de prix, les 17 contrats d assurance et le
paragraphe du delai sur les 3 pages de prix.

git n a rien signale : son index etait revenu en arriere avec l arbre, donc
"git status" affichait un depot propre et "git log" une tete coherente. Le
garde-fou du deployeur, qui refuse un arbre en retard sur origin/main, ne
pouvait pas voir la difference. SEULE la comparaison du CONTENU avec ce que
Vercel sert l a vue, les 3 fois.

LA REGLE QUI EN DECOULE. La production fait foi : elle a passe les 23 controles
et chacun de ses octets a ete verifie apres livraison. Avant d appliquer un lot,
on ecrase les fichiers vises par ce que Vercel sert. Le cout est de 1 requete
par fichier, la panne evitee est une regression livree en silence.

  python3 outils/depuis_prod.py les-prix/index.html es/los-precios/index.html
  python3 outils/depuis_prod.py --outils          # restaure outils/ lui-meme
"""
import hashlib
import os
import sys
import time
import urllib.request

D = "https://domivaro.speed-ecom.eu"
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTILS = ["faire_garde_local.py", "verif.py", "deployer.py",
          "inventaire_effectif.py", "redites.py", "depuis_prod.py"]


def servie(rel):
    """Ce que Vercel sert pour ce chemin. Un repertoire est servi par son
    index.html, l adresse ne porte donc pas le nom du fichier."""
    u = D + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
    r = urllib.request.urlopen(u + f"?v={int(time.time())}", timeout=60)
    assert r.status == 200, f"{rel} : code {r.status}"
    return r.read()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if "--outils" in args:
        args = [a for a in args if a != "--outils"] + ["outils/" + o for o in OUTILS]

    change, identiques = 0, 0
    for rel in args:
        chemin = os.path.join(RACINE, rel)
        try:
            d = servie(rel)
        except Exception as e:
            print(f"  ECHEC {rel} : {e}")
            return 1
        avant = open(chemin, "rb").read() if os.path.exists(chemin) else b""
        if hashlib.sha256(avant).hexdigest() == hashlib.sha256(d).hexdigest():
            identiques += 1
            continue
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        open(chemin, "wb").write(d)
        # relecture : on ne conclut pas d une ecriture qui a rendu la main
        assert open(chemin, "rb").read() == d, f"{rel} : relecture differente"
        print(f"  {rel} REMIS A JOUR depuis la production, {len(d)} octets, "
              f"sha {hashlib.sha256(d).hexdigest()[:12]}")
        change += 1

    print(f"{identiques} deja a jour, {change} remis a jour depuis la production.")
    if change:
        print("ATTENTION : l arbre local etait en retard. Verifier qu aucun travail "
              "en cours n a ete ecrit par-dessus une version perimee.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
