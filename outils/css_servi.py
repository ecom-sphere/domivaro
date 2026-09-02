# -*- coding: utf-8 -*-
"""PRODUIT app.css (servi) A PARTIR DE app.src.css (source commentee).
Depuis le lot 92, les commentaires de conception vivent dans app.src.css et ne
sont plus servis : 82 Ko dont 21 Ko de commentaires, 21,6 Ko gzip contre 12 Ko.
On edite TOUJOURS app.src.css, puis :
   python3 outils/css_servi.py
Le script retire les commentaires et les lignes vides, rien d autre : aucun
selecteur, aucune valeur n est reecrite, le CSS servi reste lisible et diffable.
"""
import os, re
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(RACINE, "app.src.css"), encoding="utf-8").read()
out = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
out = "\n".join(l.rstrip() for l in out.splitlines() if l.strip()) + "\n"
open(os.path.join(RACINE, "app.css"), "w", encoding="utf-8").write(out)
print("app.css : %d octets (source %d)" % (len(out.encode()), len(src.encode())))
