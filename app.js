/* Domivaro v3 : comportements. Rien ici n'est necessaire pour lire la page :
   sans JS, tout le contenu est visible et navigable. */
(function () {
  'use strict';

  var nav = document.getElementById('nav');
  var burger = document.getElementById('burger');
  var liens = document.getElementById('navliens');
  var reduit = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- 1. Le bandeau se pose des qu'on quitte le hero.
         Sonde invisible plutot qu'un ecouteur de scroll. ------------------ */
  if (nav && 'IntersectionObserver' in window) {
    var sonde = document.createElement('div');
    sonde.setAttribute('aria-hidden', 'true');
    sonde.style.cssText = 'position:absolute;top:78vh;left:0;width:1px;height:1px;pointer-events:none';
    document.body.appendChild(sonde);
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

    boite.querySelector('.sug-t').textContent = cible.t;
    var oui = boite.querySelector('.sug-oui');
    oui.textContent = cible.o;
    oui.href = cible.u;
    oui.setAttribute('hreflang', voulue);
    oui.setAttribute('lang', voulue);
    var non = boite.querySelector('.sug-non');
    non.textContent = window.SUG[courante] ? window.SUG[courante].n : 'x';
    non.addEventListener('click', function () {
      boite.hidden = true;
      try { localStorage.setItem('dv-langue-refus', voulue); } catch (e) {}
    });
    boite.hidden = false;
  })();

  /* --- 4. Revelations. Le contenu est deja visible : on n'ajoute .js-mo que si
         l'observateur existe, et un filet de securite reaffiche tout au bout de
         2,5 s au cas ou l'observateur ne se declencherait jamais (onglet cache,
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
