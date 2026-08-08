# -*- coding: utf-8 -*-
"""Cherche ce qu aucun controle ne voit : la redite A L INTERIEUR d une page.

Le garde-fou verifie que les titres sont uniques ENTRE les pages. Personne ne
verifiait qu une page ne dit pas 2 fois la meme chose, ce qui est exactement le
defaut vu sur la page de contact le 08/08 : la bande de titre annoncait
"Dites-nous ou se trouve la maison, reponse sous 24 heures", puis la section
suivante repetait "Dites-nous ou se trouve la maison, nous repondons sous
24 heures".

3 mesures, toutes sur le texte rendu par le navigateur, jamais sur la source :
  1. titre de bande et titre de section identiques ou quasi identiques ;
  2. chapeau de bande et chapeau suivant repetant la meme promesse ;
  3. n importe quelle phrase de plus de 40 signes ecrite 2 fois dans la page.

Cet instrument vit dans le depot et non dans le bac a sable : le nettoyage du
bac a sable l a deja efface 2 fois, et un instrument perdu est un defaut qui
revient. Lancer le miroir avant : cd /home/claude/domivaro && python3 -m
http.server 8123. Jamais en file://.
"""
import json
import re
import unicodedata
import urllib.request
from collections import Counter

from playwright.sync_api import sync_playwright

L = "http://localhost:8123"
JS = """()=>{
  const t = e => (e ? e.innerText.replace(/\\s+/g,' ').trim() : '');
  const main = document.querySelector('main');
  if (!main) return null;
  const ban = main.querySelector('.ban');
  return {
    h1: t(main.querySelector('h1')),
    banLede: t(ban ? ban.querySelector('.ban-lede, .lede, p') : null),
    titres: [...main.querySelectorAll('h2')].map(t),
    ledes: [...main.querySelectorAll('.lede, .ban-lede')].map(t),
    // Le sommaire d article et les cartes d index REPETENT les titres par
    // construction : c est leur role. On les exclut, sinon l instrument
    // signale 129 redites dont 126 sont voulues.
    phrases: [...main.querySelectorAll('p, li, h1, h2, h3, blockquote, figcaption')]
      .filter(e => !e.closest('.art-somm') && !e.closest('.carte') && !e.closest('.suite'))
      .map(t),
  };
}"""


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def mots(s):
    return set(norm(s).split())


def proche(a, b):
    """Jaccard sur les mots : au-dela de 0,7 les 2 phrases disent la meme chose."""
    A, B = mots(a), mots(b)
    if len(A) < 3 or len(B) < 3:
        return 0.0
    return len(A & B) / len(A | B)


sm = urllib.request.urlopen(L + "/sitemap.xml", timeout=30).read().decode()
urls = [u.replace("https://domivaro.speed-ecom.eu", "") or "/"
        for u in re.findall(r"<loc>([^<]+)</loc>", sm)]

res, tit, led, phr = {}, [], [], []
with sync_playwright() as p:
    n = p.chromium.launch()
    c = n.new_context(viewport={"width": 1440, "height": 1000}, locale="fr-FR")
    pg = c.new_page()
    for u in urls:
        pg.goto(L + u, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(80)
        d = pg.evaluate(JS)
        if not d:
            continue
        res[u] = d
        for h2 in d["titres"]:
            s = proche(d["h1"], h2)
            if s >= 0.7:
                tit.append((round(s, 2), u, d["h1"][:52], h2[:52]))
        for lede in d["ledes"][1:]:
            s = proche(d["banLede"], lede)
            if s >= 0.55:
                led.append((round(s, 2), u, d["banLede"][:56], lede[:56]))
        longues = [x for x in d["phrases"] if len(x) > 40]
        for txt, k in Counter(longues).items():
            if k > 1:
                phr.append((k, u, txt[:66]))
    n.close()

print(f"{len(res)} pages lues\n")
print(f"=== 1. le titre de page et un titre de section disent la meme chose : {len(tit)} ===")
for s, u, a, b in sorted(tit, reverse=True):
    print(f"  {s}  {u}\n       h1 : {a}\n       h2 : {b}")
print(f"\n=== 2. le chapeau de bande repete par un autre chapeau : {len(led)} ===")
for s, u, a, b in sorted(led, reverse=True):
    print(f"  {s}  {u}\n       bande : {a}\n       apres : {b}")
print(f"\n=== 3. meme phrase longue ecrite plusieurs fois dans la page : {len(phr)} ===")
for k, u, t in sorted(phr, reverse=True)[:25]:
    print(f"  x{k}  {u}  {t}")

json.dump({"titres": tit, "ledes": led, "phrases": phr},
          open("/home/claude/domivaro/outils/redites.txt", "w"), ensure_ascii=False)
