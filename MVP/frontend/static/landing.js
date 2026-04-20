/**
 * Landing page: hero shear, feature reveal, counters, dock scroll, preload.
 * Respects prefers-reduced-motion.
 */
(function () {
  'use strict';

  var reducedMotion = false;
  try {
    reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {}

  function featureReveal() {
    var els = document.querySelectorAll('[data-reveal]');
    if (!els.length) return;

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) entry.target.classList.add('revealed');
        });
      },
      { rootMargin: reducedMotion ? '0px' : '50px', threshold: 0.1 }
    );
    els.forEach(function (el) {
      observer.observe(el);
    });
  }

  /** Glitch-Animationen nur laufen lassen, wenn der Abschnitt sichtbar ist (Performance). */
  function glitchWhenVisible() {
    if (reducedMotion) return;
    var hero = document.getElementById('hero');
    var voidFooter = document.getElementById('void-footer');
    if (!hero && !voidFooter) return;
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('glitch-in-view');
          } else {
            entry.target.classList.remove('glitch-in-view');
          }
        });
      },
      { rootMargin: '20% 0px', threshold: 0 }
    );
    if (hero) observer.observe(hero);
    if (voidFooter) observer.observe(voidFooter);
  }

  function counters() {
    var cards = document.querySelectorAll('.overview-card[data-counter]');
    cards.forEach(function (card) {
      var raw = card.getAttribute('data-counter');
      var suffix = card.getAttribute('data-suffix') || '';
      if (raw === '<50' || raw == null) return;

      var num = parseFloat(raw, 10);
      if (isNaN(num)) return;

      var span = card.querySelector('.counter-num');
      if (!span) return;

      var duration = 1500;
      var start = performance.now();
      var startVal = 0;

      function tick(now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        var ease = 1 - Math.pow(1 - progress, 2);
        var current = Math.round(startVal + (num - startVal) * ease);
        span.textContent = current;
        if (progress < 1) requestAnimationFrame(tick);
      }

      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              requestAnimationFrame(tick);
              observer.disconnect();
            }
          });
        },
        { rootMargin: '100px', threshold: 0 }
      );
      observer.observe(card);
    });
  }

  function dockScroll() {
    var dock = document.querySelector('.command-dock');
    if (!dock) return;

    dock.addEventListener('click', function (e) {
      var a = e.target && e.target.closest('a[href^="#"]');
      if (!a || !a.hash) return;
      var id = a.getAttribute('href').slice(1);
      var target = document.getElementById(id);
      if (!target) return;

      e.preventDefault();
      if (reducedMotion) {
        target.scrollIntoView({ behavior: 'auto' });
      } else {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  function preload() {
    var els = document.querySelectorAll('[data-preload]');
    if (!els.length) return;

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          try {
            if ('contentVisibility' in el.style) el.style.contentVisibility = 'visible';
          } catch (err) {}
        });
      },
      { rootMargin: '600px' }
    );
    els.forEach(function (el) {
      try {
        if ('contentVisibility' in el.style) el.style.contentVisibility = 'auto';
      } catch (err) {}
      observer.observe(el);
    });
  }

  function init() {
    glitchWhenVisible();
    featureReveal();
    counters();
    dockScroll();
    preload();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
