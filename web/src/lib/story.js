// Draws a 1080x1920 story image for sharing.
//
// Not a screenshot of the card: a card is a wide block of text and a story is a
// tall one, so a capture would either crop badly or shrink to nothing. This
// composes the same content — same palette, same type, same eight-pointed star
// — into the shape the medium actually wants, and burns the address into the
// image, since a story cannot carry a working link on its own.

const W = 1080;
const H = 1920;
const PAD = 96;

const INK = '#14183a';
const INK2 = '#454b73';
const INK3 = '#7b81a3';
const PAPER = '#ffffff';
const LAPIS = '#263991';
const TURQ = '#3fc9db';
const ROSE = '#d2588b';
const GREEN = '#1cb680';
const BAND = [LAPIS, TURQ, GREEN, ROSE];

const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
const faDigits = (v) => String(v).replace(/[0-9]/g, (n) => FA_DIGITS[+n]);

const faFont = (w, s) => `${w} ${s}px Gandom, sans-serif`;
const enFont = (w, s) => `${w} ${s}px "Open Sans", sans-serif`;

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// The masthead star: two rounded squares, one turned 45 degrees.
function star(ctx, cx, cy, size) {
  const g = ctx.createLinearGradient(cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2);
  g.addColorStop(0, TURQ);
  g.addColorStop(1, LAPIS);
  ctx.fillStyle = g;
  for (const angle of [0, Math.PI / 4]) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    roundRect(ctx, -size / 2, -size / 2, size, size, size * 0.1);
    ctx.fill();
    ctx.restore();
  }
}

function tileBand(ctx, y, h) {
  const seg = 54;
  for (let x = 0, i = 0; x < W; x += seg, i++) {
    ctx.fillStyle = BAND[i % BAND.length];
    ctx.fillRect(x, y, seg, h);
  }
}

// Greedy wrap. Persian words break on spaces like any other; the shaping and
// bidi are the browser's job at fillText time.
function wrap(ctx, text, maxWidth, maxLines) {
  const words = String(text || '').split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const test = line ? line + ' ' + word : word;
    if (ctx.measureText(test).width <= maxWidth || !line) {
      line = test;
    } else {
      lines.push(line);
      line = word;
      if (lines.length === maxLines) break;
    }
  }
  if (lines.length < maxLines && line) lines.push(line);
  if (lines.length === maxLines && line && !lines.includes(line)) {
    let last = lines[maxLines - 1];
    while (last && ctx.measureText(last + '…').width > maxWidth) {
      last = last.replace(/\s*\S+$/, '');
    }
    lines[maxLines - 1] = last + '…';
  }
  return lines;
}

function drawLines(ctx, lines, x, y, lh) {
  for (const line of lines) {
    ctx.fillText(line, x, y);
    y += lh;
  }
  return y;
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    // Same-origin, so the canvas stays untainted and toBlob keeps working.
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function circleImage(ctx, img, cx, cy, d) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, d / 2, 0, Math.PI * 2);
  ctx.clip();
  // Match the CSS: cover, biased upward, because these are head-and-shoulders
  // plates where the face sits above centre.
  const scale = Math.max(d / img.width, d / img.height);
  const w = img.width * scale;
  const h = img.height * scale;
  ctx.drawImage(img, cx - w / 2, cy - h / 2 - (h - d) * 0.12, w, h);
  ctx.restore();
}

function circleMono(ctx, face, cx, cy, d, fa) {
  const g = ctx.createLinearGradient(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2);
  g.addColorStop(0, face.c1 || TURQ);
  g.addColorStop(1, face.c2 || LAPIS);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, cy, d / 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = fa ? faFont(700, d * 0.34) : enFont(700, d * 0.34);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(face.mono || '', cx, cy + d * 0.02);
  ctx.textBaseline = 'alphabetic';
}

/**
 * @param {{fa:boolean, kicker:string, title:string, body:string, meta:string,
 *          faces:Array<{src?:string,c1?:string,c2?:string,mono?:string}>,
 *          extra:number, brand:string, url:string}} d
 * @returns {Promise<Blob>}
 */
export async function renderStory(d) {
  const fa = !!d.fa;
  const font = fa ? faFont : enFont;

  // Canvas draws with whatever is loaded; ask for the faces used here first.
  if (document.fonts) {
    await Promise.all([
      document.fonts.load(font(700, 76)),
      document.fonts.load(font(400, 42)),
      document.fonts.load(font(600, 40)),
    ]).catch(() => {});
  }

  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, W, H);
  tileBand(ctx, 0, 16);
  tileBand(ctx, H - 16, 16);

  ctx.direction = fa ? 'rtl' : 'ltr';
  const startX = fa ? W - PAD : PAD;
  ctx.textAlign = fa ? 'right' : 'left';

  // Masthead.
  star(ctx, fa ? W - PAD - 26 : PAD + 26, 150, 52);
  ctx.fillStyle = INK;
  ctx.font = font(700, 46);
  ctx.fillText(d.brand, fa ? W - PAD - 76 : PAD + 76, 166);

  const maxW = W - PAD * 2;

  // Measure before drawing so the block can be centred: an event with a
  // two-line summary and one with nine should both sit on the page, not leave
  // a hole down the middle.
  ctx.font = font(700, 76);
  const titleLines = wrap(ctx, d.title, maxW, 4);
  ctx.font = font(400, 42);
  const bodyLines = d.body ? wrap(ctx, d.body, maxW, 9) : [];

  const faces = (d.faces || []).slice(0, 6);
  const D = 128;
  const blockH =
    (d.kicker ? 84 : 0) +
    titleLines.length * 100 +
    26 + 6 + 76 +
    bodyLines.length * 72 +
    (d.meta ? 78 : 0) +
    (faces.length ? 60 + D : 0);

  const TOP = 360;              // clear of the masthead
  const BOTTOM = H - 250;       // clear of the address
  let y = Math.max(TOP, Math.round((TOP + BOTTOM - blockH) / 2));

  if (d.kicker) {
    ctx.fillStyle = LAPIS;
    ctx.font = font(600, 42);
    ctx.fillText(d.kicker, startX, y);
    y += 84;
  }

  ctx.fillStyle = INK;
  ctx.font = font(700, 76);
  y = drawLines(ctx, titleLines, startX, y, 100);

  y += 26;
  ctx.fillStyle = ROSE;
  ctx.fillRect(fa ? W - PAD - 132 : PAD, y, 132, 6);
  y += 76;

  if (bodyLines.length) {
    ctx.fillStyle = INK2;
    ctx.font = font(400, 42);
    y = drawLines(ctx, bodyLines, startX, y, 72);
  }

  if (d.meta) {
    y += 18;
    ctx.fillStyle = INK3;
    ctx.font = font(400, 36);
    ctx.fillText(d.meta, startX, y);
    y += 60;
  }

  if (faces.length) {
    const step = D * 0.8;
    const imgs = await Promise.all(faces.map((f) => (f.src ? loadImage(f.src) : null)));
    const baseY = y + 60 + D / 2;
    for (let i = faces.length - 1; i >= 0; i--) {
      const cx = fa ? W - PAD - D / 2 - i * step : PAD + D / 2 + i * step;
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, baseY, D / 2 + 5, 0, Math.PI * 2);
      ctx.fillStyle = PAPER;
      ctx.fill();
      ctx.restore();
      if (imgs[i]) circleImage(ctx, imgs[i], cx, baseY, D);
      else circleMono(ctx, faces[i], cx, baseY, D, fa);
    }
    if (d.extra > 0) {
      const cx = fa ? W - PAD - D / 2 - faces.length * step : PAD + D / 2 + faces.length * step;
      ctx.fillStyle = '#e7eaf5';
      ctx.beginPath();
      ctx.arc(cx, baseY, D / 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = INK2;
      ctx.font = font(600, 40);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('+' + (fa ? faDigits(d.extra) : d.extra), cx, baseY);
      ctx.textBaseline = 'alphabetic';
      ctx.textAlign = fa ? 'right' : 'left';
    }
  }

  // The address, since a story carries no link of its own.
  ctx.fillStyle = INK3;
  ctx.font = font(600, 38);
  ctx.fillText(d.url, startX, H - 150);

  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}
