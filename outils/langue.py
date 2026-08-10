# -*- coding: utf-8 -*-
"""Cherche les endroits ou le texte trahit une traduction ou une ecriture
mecanique, sur les 108 pages et dans les 3 langues.

POURQUOI. Le site a ete ecrit en francais puis porte en espagnol et en anglais.
Une traduction fidele mot a mot reste grammaticalement juste et sonne fausse :
c est ce que Krystel a signale le 10/08. Aucun controle ne regardait la LANGUE,
le garde-fou ne verifie que les faits, la typographie et la structure.

CE QUE L INSTRUMENT MESURE, sur le texte rendu par le navigateur :
  1. les calques : tournures qui n existent que parce que l autre langue les a ;
  2. les phrases trop longues, au-dela de 32 mots, ou le lecteur decroche ;
  3. les debuts de phrase repetes dans une meme page, signe d ecriture en serie ;
  4. les mots repetes a moins de 6 mots d intervalle ;
  5. retiree le 10/08, voir la note plus bas.

IL NE CONCLUT RIEN. Il sort des CANDIDATS a relire. Une tournure signalee peut
etre parfaitement voulue. C est un projecteur, pas un juge.

Lancer le miroir avant : cd /home/claude/domivaro && python3 -m http.server 8123
"""
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict

from playwright.sync_api import sync_playwright

L = "http://localhost:8123"

# --- 1. les calques, par langue -------------------------------------------
# Chaque entree : motif, et ce qu il faudrait ecrire a la place.
CALQUES = {
 "fr": [
  (r"\bde par\b", "par, du fait de"),
  (r"\bau niveau (?:du|de la|des)\b", "dire l endroit ou l objet, pas au niveau de"),
  (r"\ben charge de\b", "chargé de"),
  (r"\bbasé sur\b", "fondé sur"),
  (r"\bsupporter\b", "prendre en charge, tolérer"),
  (r"\bopportunité de\b", "occasion de"),
  (r"\bréaliser que\b", "se rendre compte que"),
  (r"\bdéfinitivement\b", "vraiment, sans aucun doute"),
  (r"\bil est important de\b", "phrase directe"),
  (r"\bil convient de\b", "phrase directe"),
  (r"\bafin de pouvoir\b", "pour"),
  (r"\bdans le but de\b", "pour"),
  (r"\bà partir du moment où\b", "dès que, quand"),
  (r"\ben termes de\b", "dire l objet directement"),
  (r"\bun certain nombre de\b", "un chiffre, ou plusieurs"),
  (r"\bnous vous invitons à\b", "verbe direct"),
  (r"\bn hésitez pas à\b|\bn'hésitez pas à\b", "verbe direct"),
  (r"\bpermet de pouvoir\b", "permet de"),
  (r"\bau jour d aujourd hui\b|\baujourd'hui même\b", "aujourd hui"),
 ],
 "es": [
  (r"\ben base a\b", "según, a partir de"),
  (r"\ba nivel de\b", "decir el lugar o el objeto"),
  (r"\bjug(?:ar|amos) un papel\b", "calco del francés"),
  (r"\bes por eso que\b", "por eso"),
  (r"\bno dude en\b", "verbo directo"),
  (r"\bde cara a\b", "para"),
  (r"\ba nivel general\b", "en general"),
  (r"\bhacer frente a\b", "afrontar"),
  (r"\bpuesta en marcha\b", "arranque, inicio"),
  (r"\bpermite poder\b", "permite"),
  (r"\bes importante (?:de |que )\b", "frase directa"),
 ],
 "en": [
  (r"\bpermit(?:s)? to\b|\ballow(?:s)? to\b(?! \w+ (?:to|be))", "allows you to"),
  (r"\bwe propose you\b", "we offer you"),
  (r"\bin a general way\b", "generally"),
  (r"\bthe whole of\b", "all of"),
  (r"\bnotably\b", "in particular"),
  (r"\bmoreover\b", "and, also"),
  (r"\bin effect\b", "in fact"),
  (r"\beventually\b", "possibly ? faux ami du français"),
  (r"\bto profit from\b", "to benefit from"),
  (r"\bpossibility to\b", "possibility of"),
  (r"\bit is important to\b", "phrase directe"),
  (r"\bdo not hesitate to\b", "verbe direct"),
  (r"\bin order to be able to\b", "to"),
  (r"\bpreoccupation\b", "concern"),
  (r"\bassist to\b", "attend"),
 ],
}

# La mesure du passif a ete retiree le 10/08. Un etre suivi d un participe
# n est pas un passif en francais : "il est passe", "elle s etait mise",
# "le reproche est merite" etaient tous comptes. Sur les 10 pages signalees,
# la relecture n a trouve aucune phrase reellement lourde. Un instrument qui
# designe des phrases justes fait retravailler du bon texte : il vaut mieux
# pas de mesure qu une mesure fausse.

JS = """()=>{
  const m = document.querySelector('main');
  if (!m) return null;
  // on lit le texte VISIBLE, sommaire d article et cartes d index exclus :
  // ils repetent par construction et noieraient le signal.
  const bl = [...m.querySelectorAll('p, li, h1, h2, h3, blockquote, figcaption, td, th, summary')]
    .filter(e => !e.closest('.art-somm') && !e.closest('.carte') && !e.closest('.suite'))
    .filter(e => ![...e.children].some(c => ['P','LI','UL','OL','DIV'].includes(c.tagName)))
    .map(e => e.innerText.replace(/\\s+/g, ' ').trim())
    .filter(t => t.length > 2);
  return bl;
}"""


def lang(p):
    return "es" if p.startswith("/es/") else "en" if p.startswith("/en/") else "fr"


def sansacc(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def phrases(bloc):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ¿¡])", bloc) if x.strip()]


sm = urllib.request.urlopen(L + "/sitemap.xml", timeout=30).read().decode()
urls = [u.replace("https://domivaro.speed-ecom.eu", "") or "/"
        for u in re.findall(r"<loc>([^<]+)</loc>", sm)]

calq = defaultdict(list)
longues, debuts, repets = [], [], []
n_phr = Counter()

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1440, "height": 1000}, locale="fr-FR")
    pg = ctx.new_page()
    for u in urls:
        pg.goto(L + u, wait_until="networkidle", timeout=60000)
        blocs = pg.evaluate(JS) or []
        lg = lang(u)
        tetes = Counter()
        for b in blocs:
            for ph in phrases(b):
                n_phr[lg] += 1
                mots = ph.split()
                # 1. calques
                for motif, mieux in CALQUES[lg]:
                    for mm in re.finditer(motif, ph, re.I):
                        calq[(lg, motif)].append((u, mm.group(0), ph[:130], mieux))
                # 2. phrases trop longues
                # Une ligne de sources enumere des references : sa longueur est
                # sa forme, pas un defaut. 228 signalees, presque toutes des
                # sources. On les ecarte pour que le reste soit lisible.
                if len(mots) > 32 and not re.match(r"(Sources|Fuentes)\s*:", ph):
                    longues.append((len(mots), u, ph[:150]))
                # 3. debuts de phrase repetes
                if len(mots) >= 3:
                    tetes[" ".join(sansacc(w) for w in mots[:3])] += 1
                # 4. mot repete a moins de 6 mots
                vus = {}
                for i, w in enumerate(mots):
                    c = sansacc(re.sub(r"[^\w']", "", w))
                    if len(c) < 5:
                        continue
                    if c in vus and i - vus[c] <= 6:
                        repets.append((u, c, ph[:130]))
                    vus[c] = i
        for t, k in tetes.items():
            if k >= 3:
                debuts.append((k, u, t))
    nav.close()

print(f"{len(urls)} pages lues, phrases analysees : {dict(n_phr)}\n")
print(f"=== 1. CALQUES ET TOURNURES A REVOIR ===")
tot = sum(len(v) for v in calq.values())
for (lg, motif), occ in sorted(calq.items(), key=lambda kv: -len(kv[1])):
    print(f"\n  [{lg}] {motif}  x{len(occ)}   -> {occ[0][3]}")
    for u, trouve, ph, _ in occ[:4]:
        print(f"        {u}\n          ...{ph}")
print(f"\n  total : {tot}\n")
print(f"=== 2. PHRASES DE PLUS DE 32 MOTS : {len(longues)} ===")
for n, u, ph in sorted(longues, reverse=True)[:12]:
    print(f"  {n} mots  {u}\n     {ph}")
print(f"\n=== 3. MEME DEBUT DE PHRASE 3 FOIS OU PLUS DANS UNE PAGE : {len(debuts)} ===")
for k, u, t in sorted(debuts, reverse=True)[:12]:
    print(f"  x{k}  {u}  \"{t}...\"")
print(f"\n=== 4. MOT REPETE A MOINS DE 6 MOTS : {len(repets)} ===")
for u, c, ph in repets[:12]:
    print(f"  {c:16} {u}\n     {ph}")

json.dump({"calques": {f"{k[0]}|{k[1]}": v for k, v in calq.items()},
           "longues": longues, "debuts": debuts, "repets": repets},
          open("/home/claude/domivaro/outils/langue.txt", "w"), ensure_ascii=False)
