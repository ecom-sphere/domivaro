# -*- coding: utf-8 -*-
"""INVENTAIRE DES OCCURRENCES CHIFFREES DE L EFFECTIF.

Section 6 du brief marketing du 08/08/2026 : la decision est de GARDER la
promesse "nous sommes 2". Cet inventaire n existe donc pas pour preparer une
reecriture, il existe pour que le jour ou la promesse changera (recrutement,
ou depassement d environ 45 maisons) le remplacement soit une transformation
a comptages en une passe, et non une fouille d une demi-journee.

Sortie : fichier, langue, ligne, phrase exacte. Le total est affiche.
Aucune ecriture, lecture seule.

   cd /home/claude/domivaro && python3 outils/inventaire_effectif.py
   cd /home/claude/domivaro && python3 outils/inventaire_effectif.py --sql
"""
import html
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Un mot d effectif accole au chiffre 2, dans les 3 langues.
# On ne cherche PAS le chiffre 2 seul : le site en contient des centaines qui
# ne parlent pas de l effectif (2 heures de main d oeuvre, 2 passages par mois,
# 2 facons d arreter, un recu signe des 2 cotes, elle a grandi entre 2 pays).
# Chaque motif exige soit un nom d effectif, soit une tournure ou le 2 ne peut
# designer que Fabrizio et Krystelle.
NOMS = (r"personnes?|personas?|people|persons?|"
        r"associ[ée]s?|socios?|partners?|"
        r"g[ée]rants?|administradores?|administrateurs?|managers?|"
        r"fondateurs?|fundadores?|founders?")

MOTIFS = [
    # "2 personnes", "los 2 socios", "the 2 partners", "des 2 associes"
    re.compile(r"\b2\s+(?:%s)\b" % NOMS, re.I),
    # "les 2 gerants", "los 2 socios", "both partners"
    re.compile(r"\b(?:les|los|las|the|ambos|ambas|both)\s+2\s+(?:%s)\b" % NOMS, re.I),
    # "nous sommes 2", "somos 2", "we are 2", "ils sont 2"
    re.compile(r"\b(?:nous\s+sommes|s[oó]lo\s+somos|somos|we\s+are|they\s+are|ils\s+sont|elles\s+sont)\s+2\b", re.I),
    # "l un des 2", "uno de los 2", "one of the 2" : le 2 ne peut designer qu eux
    re.compile(r"\b(?:l['’]un|l['’]une|uno|una|one|el\s+otro)\s+(?:des|de\s+los|de\s+las|of\s+the|de\s+nosotros)\s+2\b", re.I),
    # "chacun des 2 gerants", "cada uno de los 2 socios", "each of the 2 partners"
    re.compile(r"\b(?:chacun|chacune|cada|each|either)\b[^.]{0,26}\b2\s+(?:%s)\b" % NOMS, re.I),
    # "a nous 2", "entre nous 2", "los 2 juntos" : effectif sans nom mais sans ambiguite
    re.compile(r"\b(?:[àa]|entre)\s+nous\s+2\b|\blos\s+2\s+juntos\b|\bthe\s+2\s+of\s+us\b", re.I),
]

BALISE = re.compile(r"<[^>]+>")
ESPACES = re.compile(r"[\s ]+")


def langue(chemin_relatif):
    if chemin_relatif.startswith("es/"):
        return "es"
    if chemin_relatif.startswith("en/"):
        return "en"
    return "fr"


def phrases(texte):
    """Decoupe grossierement en phrases lisibles pour un humain."""
    for brut in re.split(r"(?<=[.!?:])\s+", texte):
        net = ESPACES.sub(" ", brut).strip()
        if net:
            yield net


def main():
    trouvees = []
    fichiers = []
    for dossier, _, noms in os.walk(RACINE):
        if "/.git" in dossier:
            continue
        for nom in sorted(noms):
            if nom.endswith(".html"):
                fichiers.append(os.path.join(dossier, nom))
    fichiers.sort()

    for chemin in fichiers:
        rel = os.path.relpath(chemin, RACINE)
        brut = open(chemin, encoding="utf-8").read()
        # On retire scripts et styles : le JSON-LD ne porte pas de promesse au lecteur.
        corps = re.sub(r"<script.*?</script>|<style.*?</style>", " ", brut, flags=re.S)
        texte = html.unescape(BALISE.sub(" ", corps))
        for phrase in phrases(texte):
            for numero, motif in enumerate(MOTIFS):
                for trouve in motif.finditer(phrase):
                    debut = max(0, trouve.start() - 70)
                    trouvees.append({
                        "fichier": rel,
                        "langue": langue(rel),
                        "motif": numero,
                        "tour": trouve.group(0),
                        "position": trouve.start(),
                        "phrase": phrase[debut:trouve.end() + 70].strip(),
                    })

    # Dedoublonnage : une meme position ne peut etre comptee 2 fois, meme si
    # 2 motifs la reconnaissent. La position est unique dans le fichier.
    vues = set()
    net = []
    for t in sorted(trouvees, key=lambda x: (x["fichier"], x["position"], x["motif"])):
        cle = (t["fichier"], t["phrase"], t["tour"])
        if cle not in vues:
            vues.add(cle)
            net.append(t)

    if "--sql" in sys.argv:
        print(json.dumps(net, ensure_ascii=False, indent=1))
        return 0

    par_fichier = {}
    for t in net:
        par_fichier.setdefault(t["fichier"], []).append(t)

    for fichier in sorted(par_fichier):
        lot = par_fichier[fichier]
        print(f"\n{fichier}  [{lot[0]['langue']}]  {len(lot)} occurrence(s)")
        for t in lot:
            print(f"    . [{t['tour']}]  {t['phrase']}")

    par_langue = {}
    for t in net:
        par_langue[t["langue"]] = par_langue.get(t["langue"], 0) + 1

    # 2e compte, sur la source HTML brute. C est CELUI-LA qui sert le jour d une
    # transformation a comptages : il inclut les attributs title, alt, aria-label
    # et les balises meta, que le compte visible ci-dessus ne voit pas.
    brut_total, brut_fichiers, brut_langues = 0, set(), {}
    for chemin in fichiers:
        rel = os.path.relpath(chemin, RACINE)
        source = open(chemin, encoding="utf-8").read()
        n = sum(len(motif.findall(source)) for motif in MOTIFS)
        if n:
            brut_total += n
            brut_fichiers.add(rel)
            lg = langue(rel)
            brut_langues[lg] = brut_langues.get(lg, 0) + n

    print("\n" + "=" * 72)
    print(f"TEXTE VISIBLE : {len(net)} occurrences sur {len(par_fichier)} fichiers.")
    print("  par langue : " + ", ".join(f"{k} {v}" for k, v in sorted(par_langue.items())))
    print(f"SOURCE HTML  : {brut_total} occurrences sur {len(brut_fichiers)} fichiers.")
    print("  par langue : " + ", ".join(f"{k} {v}" for k, v in sorted(brut_langues.items())))
    print(f"{len(fichiers)} fichiers HTML lus.")
    print("Le compte SOURCE HTML est celui a reprendre le jour d une transformation.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
