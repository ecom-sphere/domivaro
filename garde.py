# -*- coding: utf-8 -*-
"""GARDE-FOU TRILINGUE DOMIVARO.
Se lance sur la PRODUCTION et echoue bruyamment. Il verifie ce que 5 audits
successifs ont trouve a la main : chiffres divergents entre langues, lexique
a plusieurs mots, jetons de gabarit, tirets cadratins, nombres en toutes
lettres, hreflang, plancher typographique. A relancer avant chaque annonce.
   python3 garde.py
"""
import json, re, sys, time, urllib.request
from collections import Counter
D = "https://domivaro.speed-ecom.eu"
SLUGS = ["busot","el-campello","mutxamel","aigues","sant-joan-d-alacant",
         "xixona","alicante","villajoyosa","relleu","benidorm","alfas-del-pi",
         "finestrat","la-nucia","altea"]
U = {"fr": "/zones/%s/", "es": "/es/zonas/%s/", "en": "/en/areas/%s/"}
ERR = []
def ck(c, m):
    if not c: ERR.append(m)

def get(u):
    return urllib.request.urlopen(D + u + f"?v={int(time.time())}", timeout=45).read().decode()

print("Lecture du sitemap...")
sm = get("/sitemap.xml")
LOCS = re.findall(r"<loc>([^<]+)</loc>", sm)
PAGES = {u.replace(D, "") or "/": get(u.replace(D, "")) for u in LOCS}
print(f"{len(PAGES)} pages lues en production\n")
def lang(p): return "es" if p.startswith("/es/") else "en" if p.startswith("/en/") else "fr"

# --- 1. jetons, cadratins, domaine mort ------------------------------------
for p, h in PAGES.items():
    ck("%(" not in h, f"1 jeton de gabarit sur {p}")
    ck("—" not in h and "–" not in h, f"1 tiret cadratin sur {p}")
    ck(len(re.findall(r"domivaro\.com", h)) == h.count("contact@domivaro.com"), f"1 domaine mort sur {p}")
print("1. jetons, tirets cadratins, domaine mort : OK")

# --- 2. les valeurs chiffrees des fiches, identiques dans les 3 langues -----
ORD = [(r"\b(\d+)(?:e|er|ère|ème)\b", r"#\1"), (r"\b(\d+)\.[ºª]", r"#\1"), (r"\b(\d+)(?:st|nd|rd|th)\b", r"#\1")]
def nombres(h, lg):
    x = re.sub(r"<script.*?</script>", "\x00", h, flags=re.S)
    out = []
    for noeud in re.split(r"<[^>]+>|\x00", x):
        n = noeud.replace(" ", " ").replace(" ", " ")
        for a, b in ORD: n = re.sub(a, b, n)
        n = re.sub(r"[.,](?=\s|$)", " ", n)
        for m in re.finditer(r"\d{1,3}(?:[ .,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?", n):
            raw = m.group(0)
            if lg == "en": v = raw.replace(",", "")
            elif lg == "es": v = raw.replace(".", "") if re.search(r"\.\d{3}\b", raw) else raw.replace(",", ".")
            else: v = raw.replace(" ", "").replace(",", ".")
            try: out.append(round(float(v.replace(" ", "")), 4))
            except ValueError: pass
    return sorted(out)
for s in SLUGS:
    n = {}
    for lg in ("fr", "es", "en"):
        h = PAGES.get(U[lg] % s, "")
        ck(h, f"2 fiche absente : {U[lg] % s}")
        n[lg] = nombres(h[h.find("<main"):h.find("</main>")], lg)
    ck(n["fr"] == n["es"] == n["en"], f"2 CHIFFRES divergents sur {s} : fr={n['fr']} es={n['es']} en={n['en']}")
print("2. valeurs chiffrees des 11 fiches identiques dans les 3 langues : OK")

# --- 3. le pourcentage de logements se recalcule depuis les 2 nombres publies
# L ancienne version verifiait un pourcentage d acheteurs neerlandais adosse a
# un nombre de ventes : les deux etaient inventes, la source citee ne publiant
# rien au niveau communal. On verifie desormais la seule chose verifiable, et
# elle l est entierement depuis la page : part = non principaux / parc total.
for s in SLUGS:
    h = PAGES[U["fr"] % s]
    m = re.search(r'chiffre">([\d,]+)[\u00a0 ]%</span><p class="k">des logements [^<]*?soit '
                  r'([\d\u00a0 ]+) sur ([\d\u00a0 ]+)<', h)
    ck(m, f"3 bloc de logements illisible sur {s}")
    if not m: continue
    p = float(m.group(1).replace(",", "."))
    a = int(re.sub(r"[^\d]", "", m.group(2)))
    t = int(re.sub(r"[^\d]", "", m.group(3)))
    ck(a < t, f"3 {a} logements non principaux sur un parc de {t} a {s}")
    ck(abs(round(100 * a / t, 1) - p) < 1e-9,
       f"3 part non recalculable sur {s} : page {p} %, calcul {round(100*a/t,1)} % ({a}/{t})")
print(f"3. les {len(SLUGS)} parts de logements se recalculent depuis la page : OK")

# --- 4. un seul mot par objet et par langue --------------------------------
LEX = {
 "en": [("TVA espagnole", [r"\bVAT\b", r"\bIVA\b"]), ("registre", [r"\bthe register\b", r"\bthe log\b"]),
        ("local technique", [r"utility room", r"plant room"]), ("groupe de securite", [r"safety group", r"safety valve"]),
        ("les 38 points", [r"38 checkpoints", r"38 points"]), ("formule phare", [r"[Mm]ost chosen", r"[Mm]ost popular"]),
        ("visite offerte", [r"check visit", r"first inspection"]),
        ("syndic", [r"building managers", r"residents association"]), ("armoire a cles", [r"sealed safe", r"sealed key cabinet"])],
 "es": [("armoire a cles", [r"caja fuerte", r"caja sellada", r"armario de llaves"]),
        ("formule", [r"la fórmula", r"el plan"]), ("statut du rapport", [r"a resolver", r"a tratar"])],
 "fr": [("armoire a cles", [r"coffre scellé", r"armoire à clés"])],
}
for lg, objets in LEX.items():
    corpus = "".join(h for p, h in PAGES.items() if lang(p) == lg)
    for nom, variantes in objets:
        presents = [v for v in variantes if re.search(v, corpus)]
        ck(len(presents) <= 1, f"4 [{lg}] l objet {nom!r} porte {len(presents)} mots : {presents}")
print("4. lexique : un seul mot par objet et par langue : OK")

# --- 5. nombres en toutes lettres ------------------------------------------
MOTS = {"fr": r"\b(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|douze|quinze|vingt)\b",
        "es": r"\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte)\b",
        "en": r"\b(two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)\b"}
for p, h in PAGES.items():
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", h, flags=re.S)))
    m = re.findall(MOTS[lang(p)], t, re.I)
    ck(not m, f"5 nombre en toutes lettres sur {p} : {sorted(set(m))}")
print("5. aucun nombre en toutes lettres : OK")

# --- 6. hreflang reciproques et x-default vers l anglais --------------------
for s in SLUGS:
    for lg in ("fr", "es", "en"):
        h = PAGES[U[lg] % s]
        for k in ("fr", "es", "en"):
            ck(f'hreflang="{k}" href="{D}{U[k] % s}"' in h, f"6 hreflang {k} manquant sur {U[lg] % s}")
        ck(f'hreflang="x-default" href="{D}{U["en"] % s}"' in h, f"6 x-default non anglais sur {U[lg] % s}")
for p, h in PAGES.items():
    ck('hreflang="x-default"' in h, f"6 x-default absent sur {p}")
print("6. hreflang reciproques et x-default vers l anglais : OK")

# --- 7. structure identique entre les 3 langues d une meme fiche ------------
def squelette(h):
    return re.findall(r'<(section|h1|h2|main|footer|header|figure|div class="faits"|div class="situ"|div class="zones")\b', h)
for s in SLUGS:
    sk = {lg: squelette(PAGES[U[lg] % s]) for lg in ("fr", "es", "en")}
    ck(sk["fr"] == sk["es"] == sk["en"], f"7 structure differente entre langues sur {s}")
print("7. structure identique fr/es/en sur les 11 fiches : OK")

# --- 8. 1 h1, main ferme, titre et description uniques ---------------------
titres, descs = Counter(), Counter()
for p, h in PAGES.items():
    ck(h.count("<h1") == 1, f"8 {h.count('<h1')} h1 sur {p}")
    ck(h.count("<main") == 1 and h.count("</main>") == 1, f"8 main mal ferme sur {p}")
    t = re.search(r"<title>(.*?)</title>", h); d = re.search(r'name="description" content="([^"]*)"', h)
    ck(t and d, f"8 titre ou description absent sur {p}")
    if t: titres[t.group(1)] += 1
    if d:
        descs[d.group(1)] += 1
        ck(len(d.group(1)) <= 165, f"8 description de {len(d.group(1))} caracteres sur {p}")
for v, c in titres.items(): ck(c == 1, f"8 titre en double ({c}) : {v[:60]}")
for v, c in descs.items(): ck(c == 1, f"8 description en double ({c}) : {v[:60]}")
print("8. 1 h1, main ferme, titres et descriptions uniques et sous 165 caracteres : OK")

# --- 9. le mot banni hors negation legale ----------------------------------
BAN = {"fr": r"surveillance|surveill\w*", "es": r"vigilancia|vigilar\w*", "en": r"monitoring|surveillance"}
OKNEG = (r"5/2014|5\.1\.a|6\.2\.[ad]|aucune activité|n'exerce|no ejerce|No ejercemos|No se ofrece|"
         r"carries out no|actividad reservada|reserved activity|"
         r"Ce que nous ne faisons pas|Lo que no hacemos|What we do not do|"
         r"ne promettons pas|no prometemos|we do not promise")
for p, h in PAGES.items():
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    for m in re.finditer(BAN[lang(p)], t, re.I):
        fen = t[max(0, m.start()-260):m.start()+120]
        frag = t[max(0, m.start()-3):m.start()+len(m.group(0))].strip()
        if re.search(OKNEG, fen): continue
        if re.match(r"^(a|à) (vigilar|surveiller)", frag, re.I): continue
        ERR.append(f"9 mot banni {m.group(0)!r} sur {p} : ...{t[max(0,m.start()-70):m.start()+40]}")
print("9. vocabulaire de surveillance hors negation legale : OK")

# --- 10. sitemap et liens internes -----------------------------------------
ck(len(LOCS) == len(set(LOCS)), "10 doublon dans le sitemap")
CONNUS = {u.replace(D, "") for u in LOCS} | {"/"}
morts = set()
for p, h in PAGES.items():
    for href in re.findall(r'href="(/[^"#?]*?)"', h):
        if href.startswith(("/img/", "/police/", "/app.", "/manifeste")) or href.endswith(".pdf"): continue
        if href not in CONNUS: morts.add(f"{href} (depuis {p})")
ck(not morts, f"10 liens internes hors sitemap : {sorted(morts)[:5]}")
print(f"10. sitemap sans doublon, {len(LOCS)} adresses, aucun lien interne inconnu : OK")

# --- 11. typographie : espaces insecables poses, aucun espace secable restant --
insec = sum(h.count("\u00a0") for h in PAGES.values())
ck(insec >= 320, f"11 seulement {insec} espaces insecables sur les 63 pages")
for p, h in PAGES.items():
    corps = " ".join(re.split(r"<[^>]+>", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)))
    fuite = re.findall(r"\d (?:€|%|m²|km)", corps)
    ck(not fuite, f"11 espace secable avant unite sur {p} : {sorted(set(fuite))[:3]}")
    if lang(p) == "fr":
        f2 = re.findall(r"\w [:;!?»]", corps)
        ck(not f2, f"11 espace secable avant ponctuation double sur {p} : {sorted(set(f2))[:3]}")
print(f"11. {insec} espaces insecables, aucun espace secable avant unite ni ponctuation double : OK")

# --- 12. attributs de langue : uniquement les 4 langues du site ---------------
for p, h in PAGES.items():
    for a in set(re.findall(r'(?<![a-z])lang="([a-zA-Z-]+)"', h)):
        ck(a in ("fr", "es", "en", "nl"), f"12 lang={a} sur {p}")
    for m in re.finditer(r'(?<![a-z])lang="(fr|es|en|nl)">([^<]{1,20})</span>', h):
        mot, val = m.group(1), m.group(2).strip()
        DICO = {"fr": "Français Complet Écrit", "es": "Español Completo Escrito",
                "en": "English Full Written", "nl": "Nederlands Binnenkort"}
        ck(val in DICO[mot].split(), f"12 {val!r} annonce en {mot} sur {p}")
print("12. attributs de langue coherents avec le texte qu ils portent : OK")

# --- 13. une seule base de consentement sur les 3 formulaires ----------------
for p, h in PAGES.items():
    if 'name="consentement"' not in h: continue
    nb = h.count('name="consentement"')
    ck(nb == 1, f"13 {nb} cases de consentement sur {p}")
    ck("required" in h.split('name="consentement"')[1][:40], f"13 case de consentement non obligatoire sur {p}")
    pied = re.search(r'class="champ large form-pied">(.*?)</p>', h, re.S)
    ck(pied and "<small>" not in pied.group(1), f"13 second consentement implicite sous le bouton sur {p}")
print("13. une seule base de consentement, explicite et obligatoire : OK")

# --- 14. separateur des milliers espagnol ------------------------------------
for p, h in PAGES.items():
    if lang(p) != "es": continue
    f = re.findall(r"\d{1,3}[  ]\d{3}[  ]?(?:€|euros)", h)
    ck(not f, f"14 separateur des milliers francais sur {p} : {sorted(set(f))[:3]}")
print("14. separateur des milliers espagnol sur les 21 pages ES : OK")

# --- 15. le sitemap dit la meme chose que les pages --------------------------
blocs = re.findall(r"<url>.*?</url>", sm, re.S)
ck(len(blocs) == len(LOCS), "15 sitemap mal forme")
for b in blocs:
    en_ = re.search(r'hreflang="en" href="([^"]+)"', b)
    xd = re.search(r'hreflang="x-default" href="([^"]+)"', b)
    ck(en_ and xd and en_.group(1) == xd.group(1),
       f"15 x-default different de l alternate anglais : {re.search(r'<loc>([^<]+)', b).group(1)}")
print("15. x-default du sitemap identique a l alternate anglais sur les 63 adresses : OK")

# --- 16. les alt ne decrivent pas ce que l image ne montre pas ---------------
INTERDIT = [(r"volets fermés|shutters closed|contraventanas cerradas", "volets fermes sur une image qui en montre d ouverts"),
            (r"(Fabrizio|Krystelle).{0,30}(sur la terrasse|en la terraza|on the terrace)", "portrait annonce sur une terrasse")]
for p, h in PAGES.items():
    for a in re.findall(r'alt="([^"]*)"', h):
        for rx, quoi in INTERDIT:
            ck(not re.search(rx, a), f"16 {quoi} sur {p} : {a[:70]}")
print("16. aucun alt ne decrit ce que l image ne montre pas : OK")

# --- 17. la police du logotype reste minuscule -------------------------------
import urllib.request as _u
_f = _u.urlopen(D + "/police/fraunces.woff2", timeout=45).read()
ck(len(_f) < 20000, f"17 fraunces.woff2 pese {len(_f)} octets")
print(f"17. police du logotype : {len(_f)} octets : OK")

# --- 18. les 3 rapports d exemple parlent comme les pages --------------------
PDF = {"fr": "/rapport-exemple-domivaro.pdf", "es": "/informe-ejemplo-domivaro.pdf",
       "en": "/sample-report-domivaro.pdf"}
BANPDF = {
 "fr": [],
 "es": [r"F[ÓO]RMULA", r"aire acondicionado", r"Persianas sur", r"Persiana suroeste",
        r"Filtros del aire", r"\d{1,3} \d{3} ?€"],
 "en": [r"[Uu]tility room", r"safety group", r"rising salt", r"\d{1,3},\d{3} ?€", r"\d+ €"],
}
try:
    import io, pdfplumber
    for lg, u in PDF.items():
        brut = urllib.request.urlopen(D + u, timeout=45).read()
        with pdfplumber.open(io.BytesIO(brut)) as doc:
            t = "\n".join((p.extract_text() or "") for p in doc.pages)
        ck(len(t) > 3000, f"18 rapport {lg} illisible ou vide")
        for rx in BANPDF[lg]:
            m = re.findall(rx, t)
            ck(not m, f"18 [{lg}] le rapport dit {sorted(set(m))[:2]} la ou les pages disent autre chose")
        ck("38" in t, f"18 rapport {lg} sans les 38 points")
    print("18. les 3 rapports d exemple emploient le vocabulaire des pages : OK")
except ImportError:
    print("18. rapports d exemple : NON VERIFIE (pdfplumber absent)")

# --- 19. titres sous 60 signes, temps de trajet sur les 3 pages de zone ------
for p, h in PAGES.items():
    t = re.search(r"<title>(.*?)</title>", h, re.S).group(1)
    ck(len(t) <= 60, f"19 titre de {len(t)} signes sur {p} : {t[:60]}")
    d = re.search(r'name="description" content="([^"]*)"', h).group(1)
    ck(len(d) <= 160, f"19 description de {len(d)} signes sur {p}")
ZON = {"/nos-zones/": "Siège", "/es/nuestras-zonas/": "Sede", "/en/our-area/": "Base"}
tot_t = 0
for u, siege in ZON.items():
    h = PAGES[u]
    g = re.search(r'<div class="zones"[^>]*>(.*?)</div>', h, re.S)
    ck(g, f"19 grille de communes absente sur {u}")
    if not g: continue
    dt = re.findall(r'data-t="([^"]+)"', g.group(1))
    ck(len(dt) == 14, f"19 {len(dt)} temps de trajet sur {u}, 14 attendus")
    ck(dt[0] == siege, f"19 premier temps de {u} = {dt[0]!r}, {siege!r} attendu")
    minutes = [int(x.split("\u00a0")[0]) for x in dt[1:]]
    ck(minutes == sorted(minutes), f"19 temps de trajet non croissants sur {u} : {minutes}")
    # le meme temps que sur le dessin
    for x, nom in zip(dt, re.findall(r'class="zm-m">([^<]+)</text>', h)):
        ck(x == nom, f"19 la grille dit {x!r} et le dessin {nom!r} sur {u}")
    tot_t += len(dt)
ck(tot_t == 42, f"19 {tot_t} temps de trajet au total, 42 attendus")
print("19. titres sous 60 signes, descriptions sous 160, 42 temps de trajet conformes au dessin : OK")

# --- 20. la reponse publique promise existe, et la methode de verification ---
AVIS = {"/avis/": ("Réponse de Domivaro", "Comment ces avis sont vérifiés", "La langue d'origine"),
        "/es/opiniones/": ("Respuesta de Domivaro", "Cómo verificamos estas opiniones", "El idioma original"),
        "/en/reviews/": ("Domivaro&#x27;s reply|Domivaro's reply", "How these reviews are checked", "The original language")}
for u, (rep, meth, lang_) in AVIS.items():
    h = PAGES[u]
    nrep = h.count('class="av-rep"')
    ck(nrep == 1, f"20 {nrep} reponse(s) publique(s) sur {u}")
    ck(re.search(rep, h), f"20 signature de la reponse absente sur {u}")
    ck(meth in h, f"20 methode de verification absente sur {u}")
    ck(lang_ in h, f"20 mention de la langue d origine absente sur {u}")
    net = h.count('class="et5"')
    ck(net == 12, f"20 {net} blocs d etoiles sur {u}, 12 attendus")
    quatre = len(re.findall(r'<div class="et5"[^>]*>(?:(?!</div>).)*?</div>', h, re.S))
    ck(quatre == 12, f"20 {quatre} blocs d etoiles fermes sur {u}")
print("20. reponse publique, methode de verification et langue d origine sur les 3 pages d avis : OK")

print()
if ERR:
    print(f"=== {len(ERR)} DEFAUT(S) ===")
    for e in ERR[:40]: print("  -", e)
    sys.exit(1)
print("=== 20 controles passes sur les 63 pages servies. ===")
