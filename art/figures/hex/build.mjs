// The README badge: a hex sticker that is really a cube seen corner-on. Roger stands on the top
// face beside the runway with the hold beacon lit (standing up out of the frame, as he is taller
// than the hexagon), the left face carries the name, and the right
// face shows two flights nose to nose, held. Roger and the planes come from art/roger.json and
// art/plane.json, so the badge always matches the site.
//
// Uses the Anatomy skill's kit (MIT, github.com/wheresryan22/anatomy) for the projection. Build:
//   node art/figures/hex/build.mjs     writes hex.svg next to this file
// The kit is read from ~/.claude/skills/anatomy, or from $ANATOMY. The PNG for the README is a
// 4x headless Chrome shot of hex.svg (Geist Mono must be installed for the lettering).
import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ART = join(HERE, "..", "..");
const SKILL = process.env.ANATOMY ?? join(homedir(), ".claude", "skills", "anatomy");
const k = await import(pathToFileURL(join(SKILL, "kit", "iso-kit.mjs")).href);

const ROGER = JSON.parse(readFileSync(join(ART, "roger.json"), "utf8"));
const PLANE = JSON.parse(readFileSync(join(ART, "plane.json"), "utf8"));

const S = 100; // the cube's side
const ROGER_V = 2.1;
const ROGER_AT = [55, 47]; // where Roger stands on the top face: his centre along x, his back edge in y
const WIDTH = 208;
const HEIGHT = 286;
// Seen from this height a cube's outline is a regular hexagon. Roger stands taller than the hexagon,
// so the canvas leaves him headroom.
const P = k.fitProjection([...k.boxCorners({ x: 0, y: 0, w: S, d: S }, -S, 0), [ROGER_AT[0], ROGER_AT[1], 25 * ROGER_V]], WIDTH, HEIGHT, {
  pad: 7,
  azimuth: 45,
  elevation: (Math.atan(1 / Math.SQRT2) * 180) / Math.PI,
});

const YELLOW = ROGER.palette.Y;
const at = (point) => k.iso(point, P);
const poly = (points) => k.pathOf(points.map(at), true);
const num = (v) => +v.toFixed(3);

// One voxel run, the same shading as Fig 1: the face toward the viewer keeps the pixel's colour.
function box(plan, z, h, colour) {
  const p = k.slabOf(plan, z, h, P, 1);
  const faces = p.shades.map((d, i) => (d ? `<path data-s="${i}" d="${d}"/>` : "")).join("");
  return `<g class="vx" style="--c:${colour}">${faces}<path class="vt" d="${p.top}"/></g>`;
}

function voxels(rows, colours, [ox, oy, oz], v, t) {
  const out = [];
  for (let r = rows.length - 1; r >= 0; r--) {
    const row = rows[r];
    const z = oz + (rows.length - 1 - r) * v;
    for (let c = 0; c < row.length; ) {
      const key = row[c];
      if (key === ".") { c++; continue; }
      let end = c;
      while (row[end + 1] === key) end++;
      out.push(box({ x: ox + c * v, y: oy, w: (end - c + 1) * v, d: t, r: 0 }, z, v, colours[key]));
      c = end + 1;
    }
  }
  return out.join("");
}

const trimmed = (rows) => rows.slice(0, rows.findLastIndex((row) => /[^.]/.test(row)) + 1);

// Flat pixel art painted onto a face, at u, v in that face's own 100 by 100 square.
function flatArt(rows, colours, u, v, size, flip = false) {
  const out = [];
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const key = row[flip ? row.length - 1 - x : x];
      if (key === ".") continue;
      out.push(`<rect x="${num(u + x * size)}" y="${num(v + y * size)}" width="${num(size + 0.05)}" height="${num(size + 0.05)}" fill="${colours[key]}"/>`);
    }
  });
  return out.join("");
}

// The face's own square: u runs left to right as you look at it, v runs down from its top edge.
const face = (side, content) => {
  const origin = side === "left" ? [0, S] : [S, S];
  return `<g transform="${k.sideMatrix(origin, 0, P, side)}">${content}</g>`;
};

const hex = poly([[0, 0, 0], [S, 0, 0], [S, 0, -S], [S, S, -S], [0, S, -S], [0, S, 0]]);

// Top face: an apron with the runway along its near edge, Roger behind it, the beacon beside him.
function top() {
  const out = [`<path fill="#4a5058" d="${poly([[0, 0, 0], [S, 0, 0], [S, S, 0], [0, S, 0]])}"/>`];
  out.push(`<path fill="#1b1d21" d="${poly([[6, 64, 0], [94, 64, 0], [94, 88, 0], [6, 88, 0]])}"/>`);
  const paint = [];
  for (let i = 0; i < 5; i++) paint.push([[9, 66.6 + i * 4.2], [16, 66.6 + i * 4.2 + 2.1]]);
  for (let x = 24; x < 88; x += 11) paint.push([[x, 75.4], [x + 5.5, 76.6]]);
  out.push(paint.map(([[x0, y0], [x1, y1]]) => `<path fill="#e6e6e6" d="${poly([[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]])}"/>`).join(""));
  const lights = [];
  for (let x = 8; x <= 92; x += 10.5) lights.push(at([x, 61.5, 0]), at([x, 90.5, 0]));
  out.push(lights.map(([x, y]) => `<circle cx="${num(x)}" cy="${num(y)}" r="0.9" fill="${YELLOW}"/>`).join(""));
  // Seams where the apron's slabs meet.
  out.push(`<path d="${k.pathOf([at([0, 50, 0]), at([S, 50, 0])])}${k.pathOf([at([50, 0, 0]), at([50, 50, 0])])}" stroke="#3a4047" stroke-width=".8" fill="none"/>`);
  // Roger's contact shadow, under where he stands.
  out.push(`<path d="${k.haloOf({ x: ROGER_AT[0] - 27, y: ROGER_AT[1] - 3, w: 54, d: 13, r: 6 }, 0, 0.1, P)}" fill="#000" opacity=".5" style="filter:blur(2.4px)"/>`);
  // The hold beacon: lit, because the flights on the right face are held.
  const [bx, by] = [88, 30];
  out.push(`<circle cx="${num(at([bx, by, 6])[0])}" cy="${num(at([bx, by, 6])[1])}" r="9" fill="#ff2b3f" opacity=".55" style="filter:blur(4px)"/>`);
  out.push(k.solidSvg(k.cylinder(bx, by, 3.6, 0, 2, P, 24), { tone: "mid" }));
  out.push(`<g class="lamp">${k.solidSvg(k.cylinder(bx, by, 2.7, 2, 6, P, 24), { tone: "hi", crease: "none" })}</g>`);
  out.push(k.solidSvg(k.cylinder(bx, by, 3.2, 8, 1.2, P, 24), { tone: "mid" }));
  return out.join("");
}

// Roger, drawn after the frame so he stands up out of it.
function roger() {
  const rows = trimmed(ROGER.moods.collision.frames[0]);
  const colours = { ...ROGER.palette, ...ROGER.accent.collision };
  const [cx, y] = ROGER_AT;
  return voxels(rows, colours, [cx - (rows[0].length * ROGER_V) / 2, y, 0], ROGER_V, 6);
}

// The ground under the apron, as a cut: concrete slab, a seam, the gravel base course, then the
// block itself. Drawn the same on both sides, so every band turns the corner.
const BODY_V = 18;
function strata(id) {
  let seed = id === "left" ? 7 : 19;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const stones = [];
  for (let i = 0; i < 70; i++) {
    const tone = rand() < 0.5 ? "#7a828c" : "#3a4047";
    stones.push(`<circle cx="${num(1 + rand() * 98)}" cy="${num(8.4 + rand() * 7.6)}" r="${num(0.45 + rand() * 0.55)}" fill="${tone}"/>`);
  }
  return [
    `<defs><linearGradient id="fall-${id}" gradientUnits="userSpaceOnUse" x1="0" y1="${BODY_V}" x2="0" y2="${S}"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".42"/></linearGradient></defs>`,
    `<path fill="#30353c" d="M0 0H${S}V${S}H0Z"/>`,
    `<rect width="${S}" height="6.4" fill="#4a5058"/>`,
    `<rect y="6.4" width="${S}" height="1.2" fill="#121417"/>`,
    `<rect y="7.6" width="${S}" height="9.2" fill="#575e67"/>`,
    stones.join(""),
    `<rect y="16.8" width="${S}" height="1.2" fill="#121417"/>`,
    `<path d="M0 .5H${S}" stroke="#a3abb4" stroke-width=".8" opacity=".55"/>`,
  ].join("");
}
const fall = (id) => `<rect y="${BODY_V}" width="${S}" height="${S - BODY_V}" fill="url(#fall-${id})"/>`;

function left() {
  const ticks = [];
  for (let u = 6; u <= 94; u += 4) ticks.push(`<path d="M${u} ${BODY_V + 3}V${BODY_V + ((u - 6) % 20 ? 6 : 9)}"/>`);
  const lights = [];
  for (let u = 10; u <= 90; u += 10) lights.push(`<circle cx="${u}" cy="90" r="1.3"/>`);
  return face("left", [
    strata("left"),
    fall("left"),
    `<g stroke="#7a828c" stroke-width=".7">${ticks.join("")}</g>`,
    `<text x="50" y="59" text-anchor="middle" font-family="Geist Mono" font-weight="800" font-size="19.5" letter-spacing="-.4" fill="${YELLOW}">detente</text>`,
    `<text x="50" y="72" text-anchor="middle" font-family="Geist Mono" font-weight="500" font-size="7.6" fill="#d8dce0">traffic control</text>`,
    `<g fill="#5b626b">${lights.join("")}</g>`,
  ].join(""));
}

// Right face: two agents' flights nose to nose, with the hold bar between them.
function right() {
  const rows = trimmed(PLANE.moods.worried.frames[0]);
  const lay = { ...PLANE.shared, ...PLANE.owners.lay };
  const codex = { ...PLANE.shared, ...PLANE.owners.a };
  const size = 1.95;
  const wide = rows[0].length * size;
  return face("right", [
    strata("right"),
    fall("right"),
    // This side faces away from the light; the paint on it stays bright enough to read.
    `<rect width="${S}" height="${S}" fill="#000" opacity=".34"/>`,
    flatArt(rows, lay, 50 - wide - 3, 37, size),
    flatArt(rows, codex, 50 + 3, 37, size, true),
    `<rect x="48.6" y="29" width="2.8" height="38" rx="1" fill="#ff2b3f"/>`,
    `<text x="50" y="84" text-anchor="middle" font-family="Geist Mono" font-weight="600" font-size="8" fill="#ff6b62">HOLD</text>`,
    ].join(""));
}

const CSS = `
.vx path{stroke-width:.4px;stroke-linejoin:round}
.vx>[data-s="3"]{fill:var(--c);stroke:var(--c)}
.vx>[data-s="2"]{fill:color-mix(in srgb,var(--c),#000 18%);stroke:color-mix(in srgb,var(--c),#000 18%)}
.vx>[data-s="1"]{fill:color-mix(in srgb,var(--c),#000 34%);stroke:color-mix(in srgb,var(--c),#000 34%)}
.vx>[data-s="0"]{fill:color-mix(in srgb,var(--c),#000 48%);stroke:color-mix(in srgb,var(--c),#000 48%)}
.vx>.vt{fill:color-mix(in srgb,var(--c),#fff 16%);stroke:color-mix(in srgb,var(--c),#fff 16%)}
.lamp .iso-top,.lamp .iso-shade,.lamp .iso-fill{fill:#ff2b3f}
.lamp .iso-edge{stroke:#ff8f8f}
`;

const rim = k.pathOf([at([0, S, 0]), at([S, S, 0]), at([S, 0, 0])]);
const corner = k.pathOf([at([S, S, 0]), at([S, S, -S])]);
const svg = `<svg xmlns="http://www.w3.org/2000/svg" class="iso" data-theme="dark" viewBox="0 0 ${WIDTH} ${HEIGHT}" width="${WIDTH}" height="${HEIGHT}" role="img" aria-label="Detente: Roger on the tower beside the runway, with two flights held nose to nose">
<style>${k.ISO_CSS}${CSS}</style>
<defs><clipPath id="hex"><path d="${hex}"/></clipPath></defs>
<g clip-path="url(#hex)">${top()}${left()}${right()}</g>
<path d="${corner}" stroke="#7a828c" stroke-width=".7" opacity=".7" fill="none"/>
<path d="${rim}" stroke="#c9ced6" stroke-width="1.1" stroke-linejoin="round" fill="none"/>
<path d="${hex}" fill="none" stroke="${YELLOW}" stroke-width="5" stroke-linejoin="round"/>
${roger()}
</svg>`;
writeFileSync(join(HERE, "hex.svg"), svg);
console.log("wrote hex.svg", WIDTH, "x", HEIGHT, Math.round(svg.length / 1024), "KB");
