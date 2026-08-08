# -*- coding: utf-8 -*-
"""DERIVE garde_local.py A PARTIR DE garde.py.

garde.py melange 2 roles dans une seule constante D : la base HTTP d ou l on
telecharge les pages, et le domaine ecrit en dur dans le HTML (hreflang,
x-default, sitemap). Pour verifier un lot AVANT de le deployer, il faut lire
les pages sur un miroir local tout en continuant a attendre le domaine de
production dans le HTML. Ce script fait cette separation, sans toucher garde.py.

   H = base HTTP de telechargement   -> http://127.0.0.1:8123
   D = domaine attendu dans le HTML  -> https://domivaro.speed-ecom.eu

JAMAIS en file:// : les chemins absolus s y resolvent a la racine du disque,
et le garde-fou passe au vert sur des pages qui n existent pas.

Emploi :
   cd /home/claude/domivaro && python3 -m http.server 8123 &
   python3 outils/faire_garde_local.py && python3 garde_local.py
"""
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "garde.py")
CIBLE = os.path.join(RACINE, "garde_local.py")

H_DEFAUT = "http://127.0.0.1:8123"

# (motif, remplacement, nombre d occurrences attendu). Le script refuse d ecrire
# si un seul compte differe : c est la regle 2 du brief, une transformation ne
# s applique que si elle reconnait exactement ce qu elle croit reconnaitre.
REGLES = [
    (r'^D = "https://domivaro\.speed-ecom\.eu"$',
     'D = "https://domivaro.speed-ecom.eu"  # domaine attendu DANS le HTML\n'
     'H = "%s"  # base HTTP de telechargement, miroir local' % H_DEFAUT, 1),
    (r'urllib\.request\.urlopen\(D \+ u \+ f"\?v=\{int\(time\.time\(\)\)\}", timeout=45\)',
     'urllib.request.urlopen(H + u + f"?v={int(time.time())}", timeout=45)', 1),
    (r'_u\.urlopen\(D \+ "/police/fraunces\.woff2", timeout=45\)',
     '_u.urlopen(H + "/police/fraunces.woff2", timeout=45)', 1),
    (r'urllib\.request\.urlopen\(D \+ u, timeout=45\)',
     'urllib.request.urlopen(H + u, timeout=45)', 1),
]

ENTETE = (
    "# -*- coding: utf-8 -*-\n"
    "# FICHIER DERIVE, NE PAS MODIFIER A LA MAIN.\n"
    "# Genere par outils/faire_garde_local.py depuis garde.py.\n"
    "# H = base HTTP de telechargement (miroir local), D = domaine attendu dans le HTML.\n"
)


def main():
    if not os.path.exists(SOURCE):
        print("garde.py introuvable.")
        return 1

    texte = open(SOURCE, encoding="utf-8").read()
    origine = texte
    echecs = []

    for motif, remplacement, attendu in REGLES:
        trouve = len(re.findall(motif, texte, flags=re.M))
        if trouve != attendu:
            echecs.append(f"  motif {motif[:58]!r} : {trouve} trouvee(s), {attendu} attendue(s)")
            continue
        texte = re.sub(motif, lambda _m, r=remplacement: r, texte, flags=re.M)

    if echecs:
        print("REFUS D ECRIRE. garde.py a change, la derivation n est plus fiable :")
        print("\n".join(echecs))
        print("\nCorriger REGLES dans ce script avant de continuer.")
        return 1

    # Controle de non-regression : le sitemap est encore lu via H, et les
    # comparaisons de hreflang portent encore sur D.
    if "H + u" not in texte or 'hreflang="{k}" href="{D}' not in texte:
        print("REFUS D ECRIRE. La separation H et D n a pas produit le resultat attendu.")
        return 1
    if texte == origine:
        print("REFUS D ECRIRE. Aucun changement produit.")
        return 1

    open(CIBLE, "w", encoding="utf-8").write(ENTETE + texte)
    print(f"garde_local.py ecrit, {len(REGLES)} regles appliquees, "
          f"{len(texte)} octets.")
    print(f"H = {H_DEFAUT}   D = https://domivaro.speed-ecom.eu")
    print("Lancer d abord : python3 -m http.server 8123")
    return 0


if __name__ == "__main__":
    sys.exit(main())
