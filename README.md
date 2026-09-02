# Domivaro

Site de Domivaro : entretien et controle technique de residences secondaires
sur la Costa Blanca. Trilingue francais, espagnol, anglais. Maquette en noindex,
servie sur https://domivaro.speed-ecom.eu (Vercel).

Aucun lien avec le depot speed-reports : ce site est totalement independant.

## Etat des sources

Les scripts Python d'origine (dv3/ : build.py, zones.py, legal.py, pages.py,
faq.py, points38.py, societe.py, sitemap.py, envoi.py) vivaient dans le bac a
sable d'une session et sont PERDUS depuis le 04/08/2026. Les 41 pages HTML de ce
depot sont la seule source. Les modifications se font par transformations
programmatiques sur les HTML, avec comptage d'occurrences avant et apres
(voir system_changelog, area domivaro).

## Le jour du vrai domaine

Toutes les URL absolues (canonical, hreflang, og, sitemap, schema.org) portent
https://domivaro.speed-ecom.eu. Pour basculer sur le domaine definitif :

1. Remplacer partout `https://domivaro.speed-ecom.eu` par le domaine achete
   (sed global sur *.html, sitemap.xml, robots.txt, manifeste.webmanifest).
2. Retirer `<meta name="robots" content="noindex, nofollow">` des 41 pages.
3. Adresses email : le site affiche contact@domivaro.com, a creer ou remplacer.

## Formulaire

Le formulaire de contact envoie pour de vrai : POST vers l'Edge Function
Supabase `domivaro-form` (projet cyylcljgizqabggrpfmo), qui ecrit dans la table
`domivaro_demandes` et notifie par email. Sans JavaScript, le POST HTML revient
sur la page avec `?envoye=1`. Le parametre `?f=` prerempli le champ formule
depuis les boutons de la page des prix.

## Identite simulee

Presentation aux associes : entreprise, CIF, avis et coordonnees simules mais
credibles, voulus ainsi. Ne pas retirer le contenu de demonstration.
Les 12 valeurs d'entreprise (CIF, registre, assurance, gerants) apparaissent
dans les mentions legales des 3 langues et le JSON-LD de chaque page.

## Feuille de style

`app.css` est PRODUIT depuis `app.src.css` par `python3 outils/css_servi.py`
(commentaires et lignes vides retires). On edite app.src.css, jamais app.css.
