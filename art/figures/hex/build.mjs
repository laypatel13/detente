// The README badge: a hex sticker that is really a cube seen corner-on. The bottom half is a solid
// block with the name on its lit side and a HOLD plate on its shaded side. The top half is a glass
// case, its two back walls painted with a night sky, and in it Roger stands red-faced on his riser
// with the hold beacon lit while two flights wait nose to nose at a barrier on the runway. The glass
// is one block with a frame one texel wide and glints in its corners, like voxel-game glass. Roger and the planes
// come from art/roger.json and art/plane.json, so the badge always matches the site.
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
const ZF = -50; // the room's floor, which is the block's top
const BAND = S + ZF; // the block's height
const WT = 5; // the back walls' thickness
const RISER = { x: 9, y: 8, w: 32, d: 17, r: 1.5 };
const RISER_H = 3;
const ROGER_V = 1.3;
const ROGER_T = 5;
const ROGER_AT = [25, 12]; // his centre along x, his back edge in y
const PLANE_V = 1.75;
const PLANE_T = 7;
const RUNWAY = [57, 83]; // the runway's edges in y
const PLANE_Y = 70 - PLANE_T / 2;
const LAY_X = 7;
const CODEX_X = 54.5;
const BOOM_X = 50;
const BEACON = [86, 22];
const WIDTH = 208;
const HEIGHT = 238;
// Seen from this height a cube's outline is a regular hexagon.
const P = k.fitProjection(k.boxCorners({ x: 0, y: 0, w: S, d: S }, -S, 0), WIDTH, HEIGHT, {
  pad: 7,
  azimuth: 45,
  elevation: (Math.atan(1 / Math.SQRT2) * 180) / Math.PI,
});

const YELLOW = ROGER.palette.Y;
const RED = "#ff2b3f";
const at = (point) => k.iso(point, P);
const poly = (points) => k.pathOf(points.map(at), true);
const num = (v) => +v.toFixed(3);
const quad = ([x0, y0], [x1, y1], z) => poly([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]);
const random = (seed) => () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

// One voxel run, the same shading as the tower picture: the face toward the viewer keeps the pixel's colour.
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
const flipped = (rows) => rows.map((row) => [...row].reverse().join(""));

// A square drawn on a vertical plane: u runs left to right as you look at it, v runs down from z.
// "left" planes face +y (lit), "right" planes face +x (in shade).
const onPlane = (side, [x, y], z, content) => `<g transform="${k.sideMatrix([x, y], z, P, side)}">${content}</g>`;
// The block's two outer sides, with v measured down from the floor.
const block = (side, content) => onPlane(side, side === "left" ? [0, S] : [S, S], ZF, content);

const hex = poly([[0, 0, 0], [S, 0, 0], [S, 0, -S], [S, S, -S], [0, S, -S], [0, S, 0]]);

// The floor: an apron with the runway across its front, edge lights, seams and the shadows.
function floor() {
  const out = [`<path fill="#4a5058" d="${quad([0, 0], [S, S], ZF)}"/>`];
  const seam = (a, b) => k.pathOf([at([...a, ZF]), at([...b, ZF])]);
  out.push(`<path d="${seam([WT, 40], [S, 40])}${seam([60, WT], [60, RUNWAY[0]])}${seam([60, RUNWAY[1]], [60, S])}" stroke="#3a4047" stroke-width=".7" fill="none"/>`);
  out.push(`<path fill="#1b1d21" d="${quad([WT, RUNWAY[0]], [S, RUNWAY[1]], ZF)}"/>`);
  const paint = [];
  for (let x = WT + 4; x < S - 3; x += 9) paint.push(quad([x, 69.4], [x + 4.5, 70.6], ZF));
  // Threshold bars at the near end, where the runway meets the edge.
  for (let i = 0; i < 5; i++) paint.push(quad([S - 6, RUNWAY[0] + 2.5 + i * 4.4], [S - 1.5, RUNWAY[0] + 4.5 + i * 4.4], ZF));
  out.push(`<path fill="#e6e6e6" d="${paint.join("")}"/>`);
  const lights = [];
  for (let x = WT + 4; x <= S - 4; x += 9.5) lights.push(at([x, RUNWAY[0] - 1.6, ZF]), at([x, RUNWAY[1] + 1.6, ZF]));
  out.push(lights.map(([x, y]) => `<circle cx="${num(x)}" cy="${num(y)}" r=".8" fill="${YELLOW}"/>`).join(""));
  const shadow = (plan, z, blur, o = 0.5) => `<path d="${k.haloOf(plan, z, 0.1, P)}" fill="#000" opacity="${o}" style="filter:blur(${blur}px)"/>`;
  out.push(shadow({ x: RISER.x - 1, y: RISER.y - 1, w: RISER.w + 2, d: RISER.d + 2, r: 3 }, ZF, 1.6, 0.45));
  out.push(shadow({ x: LAY_X + 3, y: PLANE_Y - 2, w: PLANE.width * PLANE_V - 8, d: PLANE_T + 4, r: 4 }, ZF, 1.8));
  out.push(shadow({ x: CODEX_X + 5, y: PLANE_Y - 2, w: PLANE.width * PLANE_V - 8, d: PLANE_T + 4, r: 4 }, ZF, 1.8));
  return out.join("");
}

// The night sky painted on a back wall, the same height on both so it turns the corner.
function sky(id, from, to, seed, skyline, shade) {
  const rand = random(seed);
  const stars = [];
  for (let i = 0; i < 16; i++) {
    stars.push(`<circle cx="${num(from + 2 + rand() * (to - from - 4))}" cy="${num(2.5 + rand() * 24)}" r="${num(0.3 + rand() * 0.35)}" opacity="${num(0.45 + rand() * 0.5)}"/>`);
  }
  const lights = [];
  for (let u = from + 3; u < to - 1; u += 3.2) lights.push(`<circle cx="${num(u)}" cy="40.6" r=".42"/>`);
  return [
    `<defs><linearGradient id="sky-${id}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="40"><stop offset="0" stop-color="#0b1222"/><stop offset=".7" stop-color="#1d2f4f"/><stop offset="1" stop-color="#3a5680"/></linearGradient></defs>`,
    `<rect x="${from}" width="${to - from}" height="40" fill="url(#sky-${id})"/>`,
    `<g fill="#dfe6f0">${stars.join("")}</g>`,
    `<path fill="#121822" d="${skyline}"/>`,
    `<rect x="${from}" y="40" width="${to - from}" height="${BAND - 40}" fill="#23292f"/>`,
    `<rect x="${from}" y="40" width="${to - from}" height=".5" fill="#4f6a90" opacity=".6"/>`,
    `<g fill="${YELLOW}" opacity=".8">${lights.join("")}</g>`,
    `<rect x="${from}" y="${BAND - 1.4}" width="${to - from}" height="1.4" fill="#121417"/>`,
    shade ? `<rect x="${from}" width="${to - from}" height="${BAND}" fill="#000" opacity="${shade}"/>` : "",
  ].join("");
}

function walls() {
  // On the lit wall: a hangar and, far off, another tower. On the shaded one: low sheds.
  const hangar = "M14 40V35.5Q24 28.5 34 35.5V40Z";
  const tower = "M72.6 40V31.2H71.2V28.4H76.8V31.2H75.4V40Z";
  const sheds = "M18 40V37H30V40ZM31 40V36H43V40ZM61 40V37.6H70V40Z";
  const out = [
    onPlane("left", [0, WT], 0, sky("back", WT, S, 11, hangar + tower, 0)),
    onPlane("right", [WT, S], 0, sky("side", 0, S - WT, 29, sheds, 0.32)),
    // The wall tops, their cut ends at the frame, and the corner where the two meet.
    `<path fill="#7a828c" d="${quad([0, 0], [WT, S], 0)}${quad([WT, 0], [S, WT], 0)}"/>`,
    `<path fill="#575e67" d="${poly([[0, S, ZF], [WT, S, ZF], [WT, S, 0], [0, S, 0]])}"/>`,
    `<path fill="#2c3036" d="${poly([[S, 0, ZF], [S, WT, ZF], [S, WT, 0], [S, 0, 0]])}"/>`,
    `<path d="${k.pathOf([at([WT, S, 0]), at([WT, WT, 0]), at([S, WT, 0])])}" stroke="#a3abb4" stroke-width=".6" stroke-linejoin="round" fill="none"/>`,
    `<path d="${k.pathOf([at([WT, WT, 0]), at([WT, WT, ZF])])}" stroke="#05070b" stroke-width=".5" opacity=".7" fill="none"/>`,
  ];
  return out.join("");
}

// The cut through the floor at the top of the block: concrete slab, a seam, the gravel base
// course, a seam, then the block. Drawn the same on both sides, so every band turns the corner.
const CUT = 9.6;
function strata(id, seed) {
  const rand = random(seed);
  const stones = [];
  for (let i = 0; i < 60; i++) {
    const tone = rand() < 0.5 ? "#7a828c" : "#3a4047";
    stones.push(`<circle cx="${num(1 + rand() * 98)}" cy="${num(4.9 + rand() * 3.4)}" r="${num(0.35 + rand() * 0.45)}" fill="${tone}"/>`);
  }
  return [
    `<defs><linearGradient id="fall-${id}" gradientUnits="userSpaceOnUse" x1="0" y1="${CUT}" x2="0" y2="${BAND}"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".42"/></linearGradient></defs>`,
    `<rect width="${S}" height="${BAND}" fill="#30353c"/>`,
    `<rect width="${S}" height="3.6" fill="#4a5058"/>`,
    `<rect y="3.6" width="${S}" height=".8" fill="#121417"/>`,
    `<rect y="4.4" width="${S}" height="4.4" fill="#575e67"/>`,
    stones.join(""),
    `<rect y="8.8" width="${S}" height=".8" fill="#121417"/>`,
    `<path d="M0 .5H${S}" stroke="#a3abb4" stroke-width=".8" opacity=".55"/>`,
    `<rect y="${CUT}" width="${S}" height="${BAND - CUT}" fill="url(#fall-${id})"/>`,
  ].join("");
}

function left() {
  const ticks = [];
  for (let u = 6; u <= 94; u += 4) ticks.push(`<path d="M${u} ${CUT + 2}V${CUT + ((u - 6) % 20 ? 4.5 : 7)}"/>`);
  return block("left", [
    strata("left", 7),
    `<g stroke="#7a828c" stroke-width=".7">${ticks.join("")}</g>`,
    `<text x="50" y="35.5" text-anchor="middle" font-family="Geist Mono" font-weight="800" font-size="18.5" letter-spacing="-.4" fill="${YELLOW}">detente</text>`,
    `<text x="50" y="45" text-anchor="middle" font-family="Geist Mono" font-weight="500" font-size="7" fill="#d8dce0">traffic control</text>`,
  ].join(""));
}

// The shaded side: a HOLD plate between two vent grilles.
function right() {
  const slots = [];
  for (const u of [9, 75]) for (let i = 0; i < 5; i++) slots.push(`<rect x="${u}" y="${19 + i * 4.2}" width="16" height="1.7" rx=".85"/>`);
  const screws = [[31.6, 19.6], [68.4, 19.6], [31.6, 36.4], [68.4, 36.4]].map(([u, v]) => `<circle cx="${u}" cy="${v}" r=".55"/>`);
  return block("right", [
    strata("right", 19),
    `<rect width="${S}" height="${BAND}" fill="#000" opacity=".34"/>`,
    `<g fill="#121417">${slots.join("")}</g>`,
    `<rect x="30" y="18" width="40" height="20" rx="1.6" fill="#1b1d21" stroke="#5b626b" stroke-width=".6"/>`,
    `<g fill="#7a828c">${screws.join("")}</g>`,
    `<text x="50" y="31.6" text-anchor="middle" font-family="Geist Mono" font-weight="700" font-size="9.5" letter-spacing=".6" fill="#ff6b62">HOLD</text>`,
  ].join(""));
}

// The hold beacon: lit, because the flights are held.
function beacon() {
  const [bx, by] = BEACON;
  const [gx, gy] = at([bx, by, ZF + 6]);
  return [
    `<circle cx="${num(gx)}" cy="${num(gy)}" r="9" fill="${RED}" opacity=".5" style="filter:blur(4px)"/>`,
    k.solidSvg(k.cylinder(bx, by, 3.6, ZF, 2, P, 24), { tone: "mid" }),
    `<g class="lamp">${k.solidSvg(k.cylinder(bx, by, 2.7, ZF + 2, 6, P, 24), { tone: "hi", crease: "none" })}</g>`,
    k.solidSvg(k.cylinder(bx, by, 3.2, ZF + 8, 1.2, P, 24), { tone: "mid" }),
  ].join("");
}

// Roger on his riser at the back, red-faced because two flights are about to collide.
function roger() {
  const rows = trimmed(ROGER.moods.collision.frames[0]);
  const colours = { ...ROGER.palette, ...ROGER.accent.collision };
  const [cx, y] = ROGER_AT;
  const top = ZF + RISER_H;
  return [
    box(RISER, ZF, RISER_H, "#5b626b"),
    `<path d="${k.haloOf({ x: cx - 12, y: y - 1.5, w: 24, d: ROGER_T + 3, r: 3 }, top, 0.1, P)}" fill="#000" opacity=".45" style="filter:blur(1.4px)"/>`,
    voxels(rows, colours, [cx - (rows[0].length * ROGER_V) / 2, y, top], ROGER_V, ROGER_T),
  ].join("");
}

const plane = (owner, x, flip) => {
  const rows = trimmed(PLANE.moods.hold.frames[0]);
  return voxels(flip ? flipped(rows) : rows, { ...PLANE.shared, ...PLANE.owners[owner] }, [x, PLANE_Y, ZF], PLANE_V, PLANE_T);
};

// The barrier across the runway between the two noses: two posts with red lamps and a striped boom.
function boom() {
  const [y0, y1] = [RUNWAY[0] + 0.5, RUNWAY[1] - 0.5];
  const post = (y) => box({ x: BOOM_X - 1, y, w: 2, d: 2, r: 0 }, ZF, 12, "#7a828c") + box({ x: BOOM_X - 0.8, y: y + 0.2, w: 1.6, d: 1.6, r: 0 }, ZF + 12, 1.4, RED);
  const out = [post(y0 - 2)];
  const n = 8;
  const step = (y1 - y0) / n;
  for (let i = 0; i < n; i++) out.push(box({ x: BOOM_X - 0.8, y: y0 + i * step, w: 1.6, d: step, r: 0 }, ZF + 9.2, 1.8, i % 2 ? "#f2f2f2" : RED));
  out.push(post(y1));
  return out.join("");
}

// The glass, one block: a pale tint, a frame one texel wide (lit along the top and left, darker
// along the bottom and right), two glints in the upper corner and one in the lower. Laid in the
// plane it covers.
const TEXEL = 3;
const GLINTS = [
  [3, 6], [4, 5], [5, 4], [6, 3],
  [3, 10], [4, 9], [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3],
];
const LOW_GLINT = [[-4, -7], [-5, -6], [-6, -5], [-7, -4]];
// On the lid a texel diagonal would lie flat on screen, so its glints run along x, which reads as a slant.
const LID_GLINTS = [[4, 4], [5, 4], [6, 4], [7, 4], [4, 7], [5, 7], [6, 7], [7, 7], [8, 7], [9, 7], [10, 7], [11, 7]];
const LID_LOW_GLINT = [[-8, -5], [-7, -5], [-6, -5], [-5, -5]];
function glass(u0, v0, w, h, { tint, light, dark, glint }, high = GLINTS, low = LOW_GLINT) {
  const t = TEXEL;
  const rect = (x, y, rw, rh) => `M${num(x)} ${num(y)}h${num(rw)}v${num(rh)}h${num(-rw)}Z`;
  const lit = rect(u0, v0, w, t) + rect(u0, v0 + t, t, h - t);
  const shade = rect(u0 + t, v0 + h - t, w - t, t) + rect(u0 + w - t, v0 + t, t, h - 2 * t);
  const glints = [
    ...high.map(([gx, gy]) => rect(u0 + gx * t, v0 + gy * t, t, t)),
    ...low.map(([gx, gy]) => rect(u0 + w + gx * t, v0 + h + gy * t, t, t)),
  ];
  return [
    `<rect x="${u0}" y="${v0}" width="${w}" height="${h}" fill="${tint[0]}" opacity="${tint[1]}"/>`,
    `<path d="${lit}" fill="${light[0]}" opacity="${light[1]}"/>`,
    `<path d="${shade}" fill="${dark[0]}" opacity="${dark[1]}"/>`,
    `<path d="${glints.join("")}" fill="#fff" opacity="${glint}"/>`,
  ].join("");
}

// The case: one glass block, its lid between the wall tops and its two front panes down to the floor.
function cover() {
  const o = at([0, 0, 0]);
  const [ex, ey] = [at([1, 0, 0]), at([0, 1, 0])];
  const top = `matrix(${num(ex[0] - o[0])} ${num(ex[1] - o[1])} ${num(ey[0] - o[0])} ${num(ey[1] - o[1])} ${num(o[0])} ${num(o[1])})`;
  const span = S - WT;
  return [
    `<g transform="${top}">${glass(WT, WT, span, span, { tint: ["#cfeeff", 0.12], light: ["#f4fbff", 0.72], dark: ["#9cc4d8", 0.55], glint: 0.55 }, LID_GLINTS, LID_LOW_GLINT)}</g>`,
    onPlane("left", [0, S], 0, glass(WT, 0, span, -ZF, { tint: ["#cfeeff", 0.1], light: ["#eef8ff", 0.78], dark: ["#8fb6ca", 0.6], glint: 0.6 })),
    onPlane("right", [S, S], 0, glass(0, 0, span, -ZF, { tint: ["#b9dcf0", 0.08], light: ["#c9e2ef", 0.62], dark: ["#6f93a6", 0.55], glint: 0.45 })),
    `<path d="${k.pathOf([at([WT, S, 0]), at([S, S, 0]), at([S, WT, 0])])}${k.pathOf([at([S, S, 0]), at([S, S, ZF])])}" stroke="#f4fbff" stroke-width=".8" stroke-linejoin="round" opacity=".85" fill="none"/>`,
  ].join("");
}

const CSS = `
.vx path{stroke-width:.4px;stroke-linejoin:round}
.vx>[data-s="3"]{fill:var(--c);stroke:var(--c)}
.vx>[data-s="2"]{fill:color-mix(in srgb,var(--c),#000 18%);stroke:color-mix(in srgb,var(--c),#000 18%)}
.vx>[data-s="1"]{fill:color-mix(in srgb,var(--c),#000 34%);stroke:color-mix(in srgb,var(--c),#000 34%)}
.vx>[data-s="0"]{fill:color-mix(in srgb,var(--c),#000 48%);stroke:color-mix(in srgb,var(--c),#000 48%)}
.vx>.vt{fill:color-mix(in srgb,var(--c),#fff 16%);stroke:color-mix(in srgb,var(--c),#fff 16%)}
.lamp .iso-top,.lamp .iso-shade,.lamp .iso-fill{fill:${RED}}
.lamp .iso-edge{stroke:#ff8f8f}
`;

// The block's front edges at floor height, and its near corner.
const rim = k.pathOf([at([0, S, ZF]), at([S, S, ZF]), at([S, 0, ZF])]);
const corner = k.pathOf([at([S, S, ZF]), at([S, S, -S])]);
const svg = `<svg xmlns="http://www.w3.org/2000/svg" class="iso" data-theme="dark" viewBox="0 0 ${WIDTH} ${HEIGHT}" width="${WIDTH}" height="${HEIGHT}" role="img" aria-label="Detente: inside a glass case on a block, Roger watches from his riser while two flights hold nose to nose at a barrier on the runway">
<style>${k.ISO_CSS}${CSS}</style>
<defs><clipPath id="hex"><path d="${hex}"/></clipPath></defs>
<g clip-path="url(#hex)">
${floor()}${walls()}${left()}${right()}
<path d="${corner}" stroke="#7a828c" stroke-width=".7" opacity=".7" fill="none"/>
<path d="${rim}" stroke="#c9ced6" stroke-width="1.1" stroke-linejoin="round" fill="none"/>
${beacon()}${roger()}${plane("lay", LAY_X, false)}${boom()}${plane("a", CODEX_X, true)}
${cover()}
</g>
<path d="${hex}" fill="none" stroke="${YELLOW}" stroke-width="5" stroke-linejoin="round"/>
</svg>`;
writeFileSync(join(HERE, "hex.svg"), svg);
console.log("wrote hex.svg", WIDTH, "x", HEIGHT, Math.round(svg.length / 1024), "KB");
