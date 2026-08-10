# -*- coding: utf-8 -*-
"""CONTROLE AVANT ENVOI, ET MANIFESTE DU LOT.

   python3 outils/deployer.py "<message>" html=N autres=N [--sec]

Ce script NE POUSSE PAS. Il refuse ou il autorise, et il imprime le manifeste
des fichiers a envoyer. L envoi se fait ensuite en UN SEUL COMMIT par le
connecteur GitHub Deploy (push_files), jamais fichier par fichier.

Pourquoi. Le 07/08/2026, 9 envois successifs ont declenche 9 constructions
Vercel concurrentes ; l alias de production a atterri sur une version
anterieure, avec un code 200 sur toutes les pages. Un lot = un commit = une
construction supprime la cause a la racine.

Ce que le script refuse, sans exception :
  1. un seul compte de fichiers qui differe de ce qui est annonce ;
  2. un jeton de gabarit %( restant dans un HTML produit ;
  3. un tiret cadratin ou demi-cadratin dans un HTML modifie ;
  4. un nombre ecrit en toutes lettres dans un HTML modifie ;
  5. le prenom Christelle ou Krystelle au lieu de Krystel ;
  6. un fichier vide, ou non lisible en UTF-8 ;
  7. un arbre local en retard sur origin/main.

--sec fait tous les controles et s arrete avant le manifeste.
"""
import hashlib
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOMBRES = (r"z[ée]ro|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|"
           r"treize|quatorze|quinze|seize|vingt|trente|quarante|cinquante|soixante|"
           r"cent|mille|"
           r"uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|veinte|"
           r"treinta|cuarenta|cincuenta|sesenta|ciento|mil|"
           r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
           r"twenty|thirty|forty|fifty|sixty|hundred|thousand")

# Mots qui contiennent une forme de nombre sans en etre un, ou articles.
BLANCS = re.compile(r"\b(?:une?|uno|una|one|on|dont|donc|sein|seine|"
                    r"cents?|cent-ville|mille-feuille)\b", re.I)

BALISE = re.compile(r"<[^>]+>")


def git(*args):
    return subprocess.run(["git", "-C", RACINE, *args],
                          capture_output=True, text=True).stdout.strip()


def git_brut(*args):
    """Sans strip. git status --porcelain place un espace en tete de ligne pour
    un fichier modifie non indexe ; le strip global mangeait le 1er caractere
    du 1er chemin, et le fichier paraissait supprime."""
    return subprocess.run(["git", "-C", RACINE, *args],
                          capture_output=True, text=True).stdout


def texte_visible(source):
    corps = re.sub(r"<script.*?</script>|<style.*?</style>", " ", source, flags=re.S)
    return BALISE.sub(" ", corps)


def controler(rel, source):
    """Renvoie la liste des refus pour un fichier HTML."""
    refus = []
    if not source.strip():
        refus.append(f"{rel} : fichier vide")
        return refus

    n = source.count("%(")
    if n:
        refus.append(f"{rel} : {n} jeton(s) de gabarit %( restant(s)")

    visible = texte_visible(source)
    for signe, nom in (("—", "cadratin"), ("–", "demi-cadratin")):
        n = visible.count(signe)
        if n:
            refus.append(f"{rel} : {n} tiret(s) {nom}")

    n = visible.count("Christelle") + visible.count("Krystelle")
    if n:
        refus.append(f"{rel} : {n} fois Christelle ou Krystelle au lieu de Krystel")

    minuscule = visible.lower()
    trouves = [m.group(0) for m in re.finditer(r"\b(?:%s)\b" % NOMBRES, minuscule)
               if not BLANCS.fullmatch(m.group(0))]
    if trouves:
        vus = sorted(set(trouves))
        refus.append(f"{rel} : {len(trouves)} nombre(s) en toutes lettres, "
                     f"dont {', '.join(vus[:6])}")
    return refus


def main():
    args = [a for a in sys.argv[1:]]
    sec = "--sec" in args
    args = [a for a in args if a != "--sec"]

    attendus = {}
    reste = []
    for a in args:
        m = re.fullmatch(r"(html|autres)=(\d+)", a)
        if m:
            attendus[m.group(1)] = int(m.group(2))
        else:
            reste.append(a)

    message = reste[0] if reste else ""
    if not message or "html" not in attendus or "autres" not in attendus:
        print(__doc__)
        return 2

    # 7. arbre local en retard
    git("fetch", "--quiet", "origin", "main")
    retard = git("rev-list", "--count", "HEAD..origin/main")
    if retard and retard != "0":
        print(f"REFUS. L arbre local est en retard de {retard} commit(s) sur "
              f"origin/main. Remettre a niveau avant tout envoi.")
        return 1

    # -uall : sans lui, git resume un dossier neuf en une seule ligne "outils/"
    # et le compte annonce ne peut pas etre verifie fichier par fichier.
    modifies = [l[3:].strip()
                for l in git_brut("status", "--porcelain", "-uall").splitlines() if l.strip()]
    modifies = [m.split(" -> ")[-1].strip('"') for m in modifies]
    html = sorted(m for m in modifies if m.endswith(".html"))
    autres = sorted(m for m in modifies if not m.endswith(".html"))

    print(f"Message  : {message}")
    print(f"Attendu  : {attendus['html']} html, {attendus['autres']} autres")
    print(f"Constate : {len(html)} html, {len(autres)} autres\n")

    if len(html) != attendus["html"] or len(autres) != attendus["autres"]:
        print("REFUS. Le compte ne correspond pas. Rien n est envoye.")
        for f in html + autres:
            print("  " + f)
        return 1

    refus = []
    for rel in html:
        chemin = os.path.join(RACINE, rel)
        if not os.path.exists(chemin):
            refus.append(f"{rel} : supprime, le script ne gere pas les suppressions")
            continue
        try:
            source = open(chemin, encoding="utf-8").read()
        except UnicodeDecodeError:
            refus.append(f"{rel} : non lisible en UTF-8")
            continue
        refus += controler(rel, source)

    if refus:
        print(f"REFUS. {len(refus)} controle(s) en echec. Rien n est envoye :")
        for r in refus:
            print("  " + r)
        return 1

    print(f"{len(html)} fichier(s) HTML controles : "
          f"0 jeton de gabarit, 0 tiret cadratin, 0 nombre en toutes lettres, "
          f"0 Christelle et 0 Krystelle.")

    if sec:
        print("\n--sec : controle seul, manifeste non imprime.")
        return 0

    print("\nMANIFESTE, a envoyer en UN SEUL commit via push_files :")
    total = 0
    for rel in html + autres:
        octets = open(os.path.join(RACINE, rel), "rb").read()
        total += len(octets)
        print(f"  {hashlib.sha256(octets).hexdigest()[:12]}  "
              f"{len(octets):>7} o  {rel}")
    print(f"\n{len(html) + len(autres)} fichier(s), {total} octets.")
    print("Apres l envoi : python3 outils/verif.py " + " ".join(html + autres))
    return 0


if __name__ == "__main__":
    sys.exit(main())
