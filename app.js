/* Domivaro v3 : comportements. Rien ici n'est necessaire pour lire la page :
   sans JS, tout le contenu est visible et navigable. */
(function () {
  'use strict';

  var nav = document.getElementById('nav');
  var burger = document.getElementById('burger');
  var liens = document.getElementById('navliens');
  var reduit = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- 1. Le bandeau se pose AVANT que le premier texte ne l atteigne.
         La sonde etait posee a 78vh, une fraction arbitraire de l ecran : le
         titre du hero passait donc sous une barre encore transparente et se
         melangeait aux libelles du menu. Mesure du 06/08 : 74 px de
         chevauchement, sur 126 combinaisons de page et de fenetre sur 126.
         La sonde est desormais ancree sur le premier texte de la page, decalee
         vers le haut de la hauteur de la barre : elle sort du champ juste
         avant la collision, quelle que soit la taille de la fenetre.
         Toujours une sonde, jamais un ecouteur de defilement. -------------- */
  if (nav && 'IntersectionObserver' in window) {
    var repere = document.querySelector('main :is(.ariane, .fil, h1)') || document.querySelector('main');
    var sonde = document.createElement('div');
    sonde.setAttribute('aria-hidden', 'true');
    sonde.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:1px;pointer-events:none';
    document.body.appendChild(sonde);
    var poser = function () {
      /* 96 px d avance : le fond de la barre met 0,45 s a monter, il doit etre
         opaque AVANT que le texte arrive, pas pendant. */
      var marge = nav.offsetHeight + 96;
      var haut = repere ? repere.getBoundingClientRect().top + (scrollY || pageYOffset) : marge;
      sonde.style.top = Math.max(1, haut - marge) + 'px';
    };
    poser();
    addEventListener('resize', poser, { passive: true });
    addEventListener('load', poser);
    new IntersectionObserver(function (e) {
      nav.setAttribute('data-pose', e[0].isIntersecting ? '' : 'pose');
    }, { threshold: 0 }).observe(sonde);
  }

  /* --- 2. Menu mobile. Le decalage vient de la hauteur reelle du bandeau. -- */
  if (burger && liens) {
    var maj = function () {
      document.documentElement.style.setProperty('--navh', nav.offsetHeight + 'px');
    };
    maj();
    addEventListener('resize', maj, { passive: true });

    var bascule = function (ouvrir) {
      liens.setAttribute('data-ouvert', ouvrir ? '1' : '0');
      burger.setAttribute('aria-expanded', ouvrir ? 'true' : 'false');
      if (!ouvrir && liens.contains(document.activeElement)) burger.focus();
      if (ouvrir) nav.setAttribute('data-pose', 'pose');
    };
    burger.addEventListener('click', function () {
      bascule(liens.getAttribute('data-ouvert') !== '1');
    });
    liens.addEventListener('click', function (e) {
      if (e.target.closest('a')) bascule(false);
    });
    addEventListener('keydown', function (e) {
      if (e.key === 'Escape') bascule(false);
    });
  }

  /* --- 3. Le tableau des prix devient des fiches sous 720 px. Chaque cellule
         reprend son libelle depuis l'entete, pour rester lisible sans colonnes. */
  document.querySelectorAll('table.prix').forEach(function (t) {
    var tetes = [].map.call(t.querySelectorAll('thead th'), function (th) {
      return th.textContent.trim();
    });
    t.querySelectorAll('tbody tr').forEach(function (tr) {
      [].forEach.call(tr.children, function (c, i) {
        if (c.tagName === 'TD' && !c.getAttribute('data-l')) c.setAttribute('data-l', tetes[i] || '');
      });
    });
  });


  /* --- 5. Selecteur de langue. Le <details> fait deja le clavier et le sans-JS ;
         on n'ajoute que la fermeture au clic exterieur et a la touche Echap. --- */
  var lsel = document.querySelector('.lsel');
  if (lsel) {
    document.addEventListener('click', function (e) {
      if (lsel.open && !lsel.contains(e.target)) lsel.open = false;
    });
    lsel.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { lsel.open = false; lsel.querySelector('summary').focus(); }
    });
  }

  /* --- 6. Suggestion de langue. Jamais de redirection automatique : elle casse
         le referencement et retire le choix a l'utilisateur. On propose, une
         seule fois, et le refus est memorise. ------------------------------- */
  (function () {
    var boite = document.getElementById('sug');
    if (!boite || !window.SUG) return;
    var courante = document.documentElement.lang;
    var voulue = (navigator.language || '').slice(0, 2).toLowerCase();
    var cible = window.SUG[voulue];
    var refus;
    try { refus = localStorage.getItem('dv-langue-refus'); } catch (e) { refus = null; }
    if (!cible || voulue === courante || refus === voulue) return;
  if (cible.u && cible.u === location.pathname) return;

    var titre = boite.querySelector('.sug-t');
    titre.textContent = cible.t;
    titre.setAttribute('lang', voulue);
    boite.setAttribute('role', 'status');
    var oui = boite.querySelector('.sug-oui');
    oui.textContent = cible.o;
    oui.href = cible.u;
    oui.setAttribute('hreflang', voulue);
    oui.setAttribute('lang', voulue);
    var non = boite.querySelector('.sug-non');
    non.textContent = cible.n || (window.SUG[courante] ? window.SUG[courante].n : 'x');
    non.setAttribute('lang', voulue);
    non.addEventListener('click', function () {
      boite.hidden = true;
      try { localStorage.setItem('dv-langue-refus', voulue); } catch (e) {}
    });
    boite.hidden = false;
  })();


  /* --- 7. Formulaire. Envoi reel vers la fonction domivaro-form. Sans
         JavaScript, le formulaire poste en HTML et la fonction renvoie sur
         la page avec ?envoye=1 : la confirmation s affiche au retour. ---- */
  (function () {
    var f = document.getElementById('form-contact');
    if (!f) return;
    var ok = document.getElementById('form-ok');
    function confirme() {
      [].forEach.call(f.querySelectorAll('.champ, .pot'), function (el) {
        el.style.display = 'none';
      });
      var err = document.getElementById('form-err');
      if (err) err.remove();
      ok.hidden = false;
      ok.scrollIntoView({ block: 'center', behavior: reduit ? 'auto' : 'smooth' });
      ok.setAttribute('tabindex', '-1');
      ok.focus({ preventScroll: true });
    }
    if (/[?&]envoye=1/.test(location.search)) { confirme(); }
    var m = location.search.match(/[?&]f=([^&]+)/);
    if (m) {
      var sel = document.getElementById('f-formule');
      if (sel) { try { sel.value = decodeURIComponent(m[1]); } catch (e) {} }
    }
    f.addEventListener('submit', function (e) {
      if (!window.fetch) return;
      e.preventDefault();
      if (!f.reportValidity()) return;
      var btn = f.querySelector('button[type="submit"]');
      var avant = btn.textContent;
      btn.disabled = true;
      btn.textContent = f.getAttribute('data-envoi') || avant;
      var d = {};
      [].forEach.call(f.elements, function (el) {
        if (el.name) d[el.name] = el.type === 'checkbox' ? (el.checked ? '1' : '') : el.value;
      });
      d.page = location.pathname;
      fetch(f.action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(confirme)
        .catch(function () {
          btn.disabled = false;
          btn.textContent = avant;
          var err = document.getElementById('form-err');
          if (!err) {
            err = document.createElement('p');
            err.id = 'form-err';
            err.className = 'form-err';
            err.setAttribute('role', 'alert');
            f.insertBefore(err, f.querySelector('.form-pied'));
          }
          err.textContent = f.getAttribute('data-err') || 'Erreur.';
        });
    });
  })();

  /* --- 8. La bulle "Une question ?" (lot 89, demande de Krystel). Un premier
         accueil en 5 choix qui renvoient vers les pages, et WhatsApp pour
         parler a Fabrizio et Krystel. Pas de robot, pas de stockage. -------- */
  (function () {
    if (document.getElementById('form-contact')) return;
    var lg = (document.documentElement.lang || 'fr').slice(0, 2);
    var T = {
      fr: { b: 'Une question ?', t: 'Bonjour, comment pouvons-nous vous aider ?', s: 'Choisissez ce qui vous correspond, ou écrivez-nous directement.',
            w: 'Parler avec Fabrizio et Krystel sur WhatsApp', x: 'Fermer',
            l: [['Je souhaite confier le suivi de ma maison', '/la-premiere-visite/'], ['Je voudrais connaître les tarifs', '/les-prix/'],
                ['Je voudrais savoir ce qui est contrôlé', '/la-methode/'], ['Je souhaite réserver une visite', '/contact/'], ['J\'ai une autre question', '/contact/#faq']],
            m: 'Bonjour, j\'ai une question au sujet de ma maison.' },
      es: { b: '¿Alguna pregunta?', t: 'Hola, ¿cómo podemos ayudarle?', s: 'Elija lo que le corresponda, o escríbanos directamente.',
            w: 'Hablar con Fabrizio y Krystel por WhatsApp', x: 'Cerrar',
            l: [['Quiero que cuiden de mi casa', '/es/la-primera-visita/'], ['Quiero conocer los precios', '/es/los-precios/'],
                ['Quiero saber qué se revisa', '/es/el-metodo/'], ['Quiero reservar una visita', '/es/contacto/'], ['Tengo otra pregunta', '/es/contacto/#faq']],
            m: 'Hola, tengo una pregunta sobre mi casa.' },
      en: { b: 'A question?', t: 'Hello, how can we help?', s: 'Pick what fits, or write to us directly.',
            w: 'Talk to Fabrizio and Krystel on WhatsApp', x: 'Close',
            l: [['I would like my house looked after', '/en/the-first-visit/'], ['I would like to know the prices', '/en/pricing/'],
                ['I would like to know what is checked', '/en/the-method/'], ['I would like to book a visit', '/en/contact/'], ['I have another question', '/en/contact/#faq']],
            m: 'Hello, I have a question about my house.' }
    };
    var t = T[lg] || T.fr;
    var w = document.createElement('div');
    w.className = 'bulle';
    var ul = '';
    t.l.forEach(function (x) { ul += '<li><a href="' + x[1] + '">' + x[0] + '</a></li>'; });
    w.innerHTML =
      '<div class="bulle-p" id="bulle-p" role="dialog" aria-labelledby="bulle-t" hidden>' +
        '<button class="bulle-x" type="button" aria-label="' + t.x + '">&times;</button>' +
        '<h2 id="bulle-t">' + t.t + '</h2><p>' + t.s + '</p><ul>' + ul + '</ul>' +
        '<a class="btn btn-vert" rel="noopener" href="https://wa.me/34611420873?text=' + encodeURIComponent(t.m) + '">' + t.w + '</a>' +
      '</div>' +
      '<button class="bulle-b" type="button" aria-expanded="false" aria-controls="bulle-p" aria-label="' + t.b + '">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.5-4.5A8 8 0 1 1 21 12z"/></svg>' +
        '<span>' + t.b + '</span></button>';
    document.body.appendChild(w);
    var p = w.querySelector('.bulle-p'), b = w.querySelector('.bulle-b');
    var ouvrir = function (o) {
      p.hidden = !o;
      b.setAttribute('aria-expanded', o ? 'true' : 'false');
      if (o) p.querySelector('a').focus(); else b.focus();
    };
    b.addEventListener('click', function () { ouvrir(p.hidden); });
    w.querySelector('.bulle-x').addEventListener('click', function () { ouvrir(false); });
    document.addEventListener('click', function (e) { if (!p.hidden && !w.contains(e.target)) ouvrir(false); });
    addEventListener('keydown', function (e) { if (e.key === 'Escape' && !p.hidden) ouvrir(false); });
  })();

  /* --- 4. Revelations. Le contenu est deja visible : on n'ajoute .js-mo que si
         l'observateur existe, et un filet de securite reaffiche tout au bout de
         2 s au cas ou l'observateur ne se declencherait jamais (onglet cache,
         rendu sans fenetre). ------------------------------------------------ */
  if (reduit || !('IntersectionObserver' in window)) return;

  var cibles = [].slice.call(document.querySelectorAll('[data-mo], .hero-img, .doc'));
  if (!cibles.length) return;

  /* Ce qui est deja a l'ecran au chargement ne doit jamais etre masque : on lui
     retire l'attribut AVANT de poser .js-mo. Le hero garde son animation propre. */
  var aObserver = [];
  cibles.forEach(function (el) {
    if (el.closest('.hero')) { el.removeAttribute('data-mo'); return; }
    if (el.getBoundingClientRect().top < innerHeight * 0.95) { el.removeAttribute('data-mo'); return; }
    aObserver.push(el);
  });
  document.documentElement.classList.add('js-mo');

  var obs = new IntersectionObserver(function (entrees, o) {
    entrees.forEach(function (en) {
      if (en.isIntersecting) { en.target.classList.add('vu'); o.unobserve(en.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.02 });

  aObserver.forEach(function (el) { obs.observe(el); });

  /* Filet de securite : si l'observateur ne se declenche jamais, tout reapparait. */
  setTimeout(function () {
    aObserver.forEach(function (el) { el.classList.add('vu'); });
  }, 2000);
})();
