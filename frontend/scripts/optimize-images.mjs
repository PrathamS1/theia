// One-off build step: converts the raw hero art masters into web-sized WebP
// variants. Run with `npm run images` whenever the source PNGs change.
import sharp from 'sharp';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(root, '..', 'public');
const outDir = path.join(publicDir, 'img');

const jobs = [
  { src: 'BackgroundTheia.png', prefix: 'bg', widths: [1600, 2560, 3840] },
  { src: 'TheiaStatueNew.png', prefix: 'statue', widths: [900, 1400, 2000], trim: true },

  // Colonnade section (below the hero). Everything here is trimmed to its
  // alpha bbox so the artwork edge *is* the image edge -- the pillar clip and
  // the statue rest positions are expressed as percentages of the element, so
  // stray transparent padding would silently shift them.
  { src: 'statueSideways.png', prefix: 'statue-side', widths: [700, 1100, 1600], trim: true },
  { src: 'statueSidewaysSmall.png', prefix: 'statue-small', widths: [454, 908], trim: true },
  { src: 'pillar.png', prefix: 'pillar', widths: [900, 1300], trim: true },
  // Not trimmed: these two are full-width strips whose own padding is
  // load-bearing (the ceiling's edge lines, the barcode's inset lettering).
  { src: 'celling.png', prefix: 'ceiling', widths: [1600, 2400, 3600] },
  { src: 'barcode.png', prefix: 'barcode', widths: [1600, 2400] },
  { src: 'misc.png', prefix: 'misc', widths: [600, 1000], trim: true },

  // Footer. The background is a full-bleed strip, so it keeps its own edges;
  // the statue is trimmed for the same reason the colonnade ones are -- it is
  // placed with `bottom-0 left-1/2`, which only lands predictably once the
  // artwork edge is the image edge.
  { src: 'footerBg.png', prefix: 'footer-bg', widths: [1600, 2560, 3840] },
  { src: 'footerTheia.png', prefix: 'footer-statue', widths: [600, 1000, 1500], trim: true },
  // 64px tiles at 2x. Deliberately NOT trimmed: the sources are already square
  // with the tile centred, and the artwork's soft edge falls off further below
  // the tile than above it -- so an alpha bbox comes back portrait (128x152)
  // and `object-contain` then letterboxes the tile high in its square slot.
  { src: 'mail.png', prefix: 'logo-gmail', widths: [128] },
  { src: 'slack.png', prefix: 'logo-slack', widths: [128] },
  { src: 'hubspot.png', prefix: 'logo-hubspot', widths: [128] },
];

const logoJobs = [
  { src: 'Theialogo.png', out: 'theia-mark.webp' },
  { src: 'hydradblogo.png', out: 'hydradb-mark.webp' },
];

// Scans the alpha channel for the subject's real bounding box (cutout PNGs
// carry a lot of dead transparent padding) and returns an extract region
// padded by `paddingPct` of the canvas's own dimensions, clamped in-bounds.
async function alphaTrimRegion(image, paddingPct = 0.01) {
  const { data, info } = await image.clone().raw().toBuffer({ resolveWithObject: true });
  const { width, height, channels } = info;
  let minX = width, maxX = 0, minY = height, maxY = 0;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const a = data[(y * width + x) * channels + 3];
      if (a > 10) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  const padX = Math.round(width * paddingPct);
  const padY = Math.round(height * paddingPct);
  const left = Math.max(0, minX - padX);
  const top = Math.max(0, minY - padY);
  const right = Math.min(width, maxX + padX);
  const bottom = Math.min(height, maxY + padY);
  return { left, top, width: right - left, height: bottom - top };
}

await mkdir(outDir, { recursive: true });

for (const job of jobs) {
  const srcPath = path.join(publicDir, job.src);
  let base = sharp(srcPath);
  if (job.trim) {
    base = base.extract(await alphaTrimRegion(base));
  }
  for (const width of job.widths) {
    const outPath = path.join(outDir, `${job.prefix}-${width}.webp`);
    await base.clone().resize({ width }).webp({ quality: 78, effort: 6 }).toFile(outPath);
    console.log(`wrote ${path.relative(publicDir, outPath)}`);
  }
}

for (const logoJob of logoJobs) {
  const srcPath = path.join(publicDir, logoJob.src);
  const region = await alphaTrimRegion(sharp(srcPath), 0.02);
  const outPath = path.join(outDir, logoJob.out);
  await sharp(srcPath).extract(region).webp({ quality: 90, effort: 6 }).toFile(outPath);
  console.log(`wrote ${path.relative(publicDir, outPath)}`);
}
