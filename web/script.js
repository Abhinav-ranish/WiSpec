// ============================================
// WiSpec — Interactive Signal Animations
// ============================================

(function () {
  'use strict';

  // ── Hero Canvas: Tri-Band Wave Visualization ──
  const heroCanvas = document.getElementById('heroCanvas');
  if (heroCanvas) {
    const ctx = heroCanvas.getContext('2d');
    let w, h, time = 0;
    let particles = [];

    function resizeHero() {
      const dpr = window.devicePixelRatio || 1;
      w = heroCanvas.clientWidth;
      h = heroCanvas.clientHeight;
      heroCanvas.width = w * dpr;
      heroCanvas.height = h * dpr;
      ctx.scale(dpr, dpr);
    }

    function initParticles() {
      particles = [];
      const count = Math.floor(w * h / 12000);
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.2 + 0.3,
          vx: (Math.random() - 0.5) * 0.3,
          vy: (Math.random() - 0.5) * 0.3,
          alpha: Math.random() * 0.3 + 0.05
        });
      }
    }

    function drawWave(yCenter, amplitude, frequency, speed, color, alpha, lineWidth) {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = lineWidth;

      for (let x = 0; x <= w; x += 2) {
        const normalX = x / w;
        const envelope = Math.sin(normalX * Math.PI) * 0.8 + 0.2;
        const y = yCenter + Math.sin(x * frequency * 0.01 + time * speed) * amplitude * envelope;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }

      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    function drawParticles() {
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 229, 255, ${p.alpha})`;
        ctx.fill();
      }
    }

    function animateHero() {
      ctx.clearRect(0, 0, w, h);

      // Background gradient
      const grad = ctx.createRadialGradient(w * 0.5, h * 0.4, 0, w * 0.5, h * 0.5, w * 0.6);
      grad.addColorStop(0, 'rgba(0, 229, 255, 0.03)');
      grad.addColorStop(0.5, 'rgba(0, 229, 255, 0.01)');
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Particles
      drawParticles();

      const center = h * 0.5;

      // 2.4 GHz waves (cyan, lower frequency)
      drawWave(center, 30, 1.2, 0.8, '#00e5ff', 0.08, 1.5);
      drawWave(center, 40, 1.0, 0.6, '#00e5ff', 0.12, 1);
      drawWave(center, 25, 1.5, 1.0, '#00e5ff', 0.06, 0.8);

      // 5 GHz waves (green, higher frequency)
      drawWave(center, 20, 2.8, 1.4, '#39ff14', 0.06, 1.2);
      drawWave(center, 28, 2.4, 1.2, '#39ff14', 0.1, 0.8);
      drawWave(center, 15, 3.2, 1.6, '#39ff14', 0.04, 0.6);

      // 6 GHz waves (purple, highest frequency)
      drawWave(center, 14, 3.8, 1.8, '#a855f7', 0.05, 1.0);
      drawWave(center, 20, 3.4, 1.5, '#a855f7', 0.08, 0.7);
      drawWave(center, 10, 4.2, 2.0, '#a855f7', 0.03, 0.5);

      // Center glow line
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.04)';
      ctx.lineWidth = 1;
      ctx.moveTo(0, center);
      ctx.lineTo(w, center);
      ctx.stroke();

      time += 0.02;
      requestAnimationFrame(animateHero);
    }

    resizeHero();
    initParticles();
    animateHero();

    window.addEventListener('resize', () => {
      resizeHero();
      initParticles();
    });
  }

  // ── Pipeline Wave Canvases ──
  document.querySelectorAll('.pipeline-wave').forEach(canvas => {
    const ctx = canvas.getContext('2d');
    const freq = parseFloat(canvas.dataset.freq);
    const color = canvas.dataset.color;
    let time = Math.random() * 100;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.scale(dpr, dpr);
    }

    function draw() {
      const cw = canvas.clientWidth;
      const ch = canvas.clientHeight;
      ctx.clearRect(0, 0, cw, ch);

      const center = ch / 2;
      const amplitude = ch * 0.25;
      const waveFreq = freq * 0.8;

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.6;
      ctx.lineWidth = 2;

      for (let x = 0; x <= cw; x += 2) {
        const envelope = Math.sin((x / cw) * Math.PI);
        const y = center + Math.sin(x * waveFreq * 0.04 + time) * amplitude * envelope;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Faded second wave
      ctx.beginPath();
      ctx.globalAlpha = 0.2;
      ctx.lineWidth = 1;
      for (let x = 0; x <= cw; x += 2) {
        const envelope = Math.sin((x / cw) * Math.PI);
        const y = center + Math.sin(x * waveFreq * 0.04 + time + 1) * amplitude * 0.6 * envelope;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Labels rendered via HTML legend overlay

      time += 0.03;
      requestAnimationFrame(draw);
    }

    resize();
    draw();
    window.addEventListener('resize', resize);
  });

  // ── Navigation Scroll Effect ──
  const nav = document.getElementById('nav');
  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;
    if (scrollY > 80) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
    lastScroll = scrollY;
  }, { passive: true });

  // ── Mobile Nav Toggle ──
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.querySelector('.nav-links');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });

    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
      });
    });
  }

  // ── Intersection Observer: Reveal Animations ──
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const delay = parseInt(entry.target.dataset.delay || 0, 10);
          setTimeout(() => {
            entry.target.classList.add('visible');
          }, delay);
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('.reveal').forEach(el => {
    revealObserver.observe(el);
  });

  // ── Animate Material Bars on Reveal ──
  const barObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll('.material-bar-fill').forEach((bar, i) => {
            setTimeout(() => bar.classList.add('animated'), i * 150);
          });
          barObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );

  document.querySelectorAll('.material-card').forEach(card => {
    barObserver.observe(card);
  });

  // ── Animate Delta Bars ──
  const deltaObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll('.pipeline-delta-bar').forEach((bar, i) => {
            setTimeout(() => bar.classList.add('animated'), i * 120);
          });
          deltaObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );

  document.querySelectorAll('.pipeline-delta').forEach(el => {
    deltaObserver.observe(el);
  });

  // ── Animate Results Bars ──
  const resultsObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll('.results-bar').forEach((bar, i) => {
            setTimeout(() => bar.classList.add('animated'), i * 200 + 300);
          });
          resultsObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );

  document.querySelectorAll('.results-chart').forEach(el => {
    resultsObserver.observe(el);
  });

  // ── Animated Counters ──
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounters(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  document.querySelectorAll('.hero-stats').forEach(el => {
    counterObserver.observe(el);
  });

  function animateCounters(container) {
    container.querySelectorAll('[data-count]').forEach(el => {
      const target = parseInt(el.dataset.count, 10);
      const prefix = el.dataset.prefix || '';
      const duration = 1800;
      const start = performance.now();

      function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out quart
        const eased = 1 - Math.pow(1 - progress, 4);
        const current = Math.round(target * eased);
        el.textContent = prefix + current;

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      }

      requestAnimationFrame(update);
    });
  }

  // ── Copy Citation Buttons ──
  document.querySelectorAll('.cite-copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      const text = targetEl.textContent;
      navigator.clipboard.writeText(text).then(() => {
        const span = btn.querySelector('span');
        const originalText = span.textContent;
        span.textContent = 'Copied!';
        btn.classList.add('copied');

        setTimeout(() => {
          span.textContent = originalText;
          btn.classList.remove('copied');
        }, 2000);
      });
    });
  });

  // ── Smooth Scroll for Anchor Links ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();
