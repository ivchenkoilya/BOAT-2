'use strict';

(() => {
  const VERSION = 83;
  const spriteParts = { crystal: 1, drone: 2, barrier: 2 };
  const sprites = window.__ROOFTOP_OBJECT_SPRITES__ = window.__ROOFTOP_OBJECT_SPRITES__ || {};

  const fallbackCrystal = typeof drawCrystal === 'function' ? drawCrystal : null;
  const fallbackDrone = typeof drawDrone === 'function' ? drawDrone : null;
  const fallbackBarrier = typeof drawBarrier === 'function' ? drawBarrier : null;

  async function loadSprite(name, partCount) {
    const parts = await Promise.all(Array.from({ length: partCount }, async (_, index) => {
      const response = await fetch(`/boss-app/assets/rooftop_v76/${name}_v83_${index}.b64?v=${VERSION}`, { cache: 'force-cache' });
      if (!response.ok) throw new Error(`Не загружена часть HD-спрайта ${name}: ${index}`);
      return (await response.text()).trim();
    }));
    const encoded = parts.join('');
    const image = new Image();
    image.decoding = 'async';
    image.src = `data:image/avif;base64,${encoded}`;
    if (typeof image.decode === 'function') await image.decode();
    else await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; });
    sprites[name] = image;
  }

  Promise.allSettled(Object.entries(spriteParts).map(([name, partCount]) => loadSprite(name, partCount)))
    .then(results => {
      results.forEach((result, index) => {
        if (result.status === 'rejected') console.warn('HD-спрайт не загрузился:', Object.keys(spriteParts)[index], result.reason);
      });
      if (!running && typeof drawIdle === 'function') drawIdle();
    });

  drawCrystal = function drawHdCrystal(s, phase, t) {
    const image = sprites.crystal;
    if (!image) { if (fallbackCrystal) fallbackCrystal(s, phase, t); return; }

    const pulse = 1 + Math.sin(t * .007 + phase * 2.1) * .045;
    const bob = Math.sin(t * .0034 + phase) * 2.7 * s;
    const h = 62 * s * pulse;
    const w = h * image.naturalWidth / image.naturalHeight;

    ctx.save();
    ctx.translate(0, bob);
    ctx.rotate(Math.sin(t * .0018 + phase) * .045);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.shadowColor = '#bf46ff';
    ctx.shadowBlur = 23 * s;
    ctx.drawImage(image, -w / 2, -h * .55, w, h);

    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = .10 + .06 * Math.sin(t * .009 + phase);
    ctx.shadowColor = '#f2b5ff';
    ctx.shadowBlur = 32 * s;
    ctx.drawImage(image, -w * .525, -h * .575, w * 1.05, h * 1.05);
    ctx.restore();

    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    for (let i = 0; i < 6; i++) {
      const a = t * .0016 + phase + i * Math.PI / 3;
      const radius = (18 + (i % 2) * 4) * s;
      const px = Math.cos(a) * radius;
      const py = Math.sin(a) * radius * .65 + bob;
      const sparkle = 1.1 + (i % 3) * .35;
      ctx.globalAlpha = .20 + .16 * Math.sin(t * .006 + i + phase);
      ctx.fillStyle = i % 2 ? '#f4c8ff' : '#75eaff';
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 10 * s;
      ctx.beginPath();
      ctx.arc(px, py, sparkle * s, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  };

  drawBarrier = function drawHdBarrier(s, phase, t) {
    const image = sprites.barrier;
    if (!image) { if (fallbackBarrier) fallbackBarrier(s, phase, t); return; }

    const breathe = 1 + Math.sin(t * .0045 + phase) * .018;
    const w = 122 * s * breathe;
    const h = w * image.naturalHeight / image.naturalWidth;
    const y = -h + 8 * s + Math.sin(t * .003 + phase) * .7 * s;

    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.shadowColor = '#b632ff';
    ctx.shadowBlur = 20 * s;
    ctx.drawImage(image, -w / 2, y, w, h);

    const pulse = .10 + .10 * (.5 + .5 * Math.sin(t * .012 + phase));
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = pulse;
    ctx.shadowColor = '#f27cff';
    ctx.shadowBlur = 28 * s;
    ctx.drawImage(image, -w * .51, y - h * .01, w * 1.02, h * 1.02);
    ctx.restore();

    ctx.save();
    const scanX = ((t * .035 + phase * 97) % (w * 1.35)) - w * .675;
    const scan = ctx.createLinearGradient(scanX - 12 * s, 0, scanX + 12 * s, 0);
    scan.addColorStop(0, 'rgba(255,255,255,0)');
    scan.addColorStop(.5, 'rgba(239,181,255,.34)');
    scan.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.globalCompositeOperation = 'screen';
    ctx.fillStyle = scan;
    ctx.fillRect(-w / 2, y + h * .24, w, h * .48);
    ctx.restore();
  };

  drawDrone = function drawHdDrone(s, phase, t) {
    const image = sprites.drone;
    if (!image) { if (fallbackDrone) fallbackDrone(s, phase, t); return; }

    const bob = Math.sin(t * .0032 + phase) * 3.2 * s;
    const w = 116 * s;
    const h = w * image.naturalHeight / image.naturalWidth;
    const lift = -35 * s + bob;
    const beamTop = lift + h * .30;
    const beamHeight = 48 * s;
    const beamWidth = 35 * s * (1 + Math.sin(t * .006 + phase) * .05);

    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    const beam = ctx.createLinearGradient(0, beamTop, 0, beamTop + beamHeight);
    beam.addColorStop(0, 'rgba(234,165,255,.55)');
    beam.addColorStop(.36, 'rgba(176,85,255,.25)');
    beam.addColorStop(1, 'rgba(118,63,255,0)');
    ctx.fillStyle = beam;
    ctx.shadowColor = '#b55cff';
    ctx.shadowBlur = 22 * s;
    ctx.beginPath();
    ctx.moveTo(-beamWidth * .16, beamTop);
    ctx.lineTo(beamWidth * .16, beamTop);
    ctx.lineTo(beamWidth * .58, beamTop + beamHeight);
    ctx.lineTo(-beamWidth * .58, beamTop + beamHeight);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.save();
    ctx.translate(0, lift);
    ctx.rotate(Math.sin(t * .0017 + phase) * .028);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.shadowColor = '#7d35ff';
    ctx.shadowBlur = 20 * s;
    ctx.drawImage(image, -w / 2, -h / 2, w, h);

    const rotors = [
      [-.31, -.19, .155, .062], [.31, -.19, .155, .062],
      [-.28, .12, .125, .048], [.28, .12, .125, .048]
    ];
    ctx.globalCompositeOperation = 'screen';
    ctx.lineCap = 'round';
    rotors.forEach((rotor, index) => {
      const [rx, ry, rw, rh] = rotor;
      const spin = t * .018 * (index % 2 ? -1 : 1) + phase + index;
      ctx.save();
      ctx.translate(rx * w, ry * h);
      ctx.rotate(spin);
      ctx.strokeStyle = index < 2 ? 'rgba(204,104,255,.54)' : 'rgba(104,226,255,.46)';
      ctx.shadowColor = ctx.strokeStyle;
      ctx.shadowBlur = 9 * s;
      ctx.lineWidth = 1.3 * s;
      ctx.beginPath();
      ctx.ellipse(0, 0, rw * w, rh * h, 0, -.75, .75);
      ctx.stroke();
      ctx.beginPath();
      ctx.ellipse(0, 0, rw * w, rh * h, 0, Math.PI - .75, Math.PI + .75);
      ctx.stroke();
      ctx.restore();
    });

    const lensPulse = .65 + .35 * Math.sin(t * .010 + phase);
    const lens = ctx.createRadialGradient(0, h * .025, 0, 0, h * .025, 8 * s);
    lens.addColorStop(0, `rgba(255,255,255,${.82 * lensPulse})`);
    lens.addColorStop(.25, `rgba(255,62,160,${.72 * lensPulse})`);
    lens.addColorStop(1, 'rgba(178,41,255,0)');
    ctx.fillStyle = lens;
    ctx.beginPath();
    ctx.arc(0, h * .025, 8 * s, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };
})();
