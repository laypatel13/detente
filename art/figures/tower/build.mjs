// The tower picture for the README and the Docs page. An airfield model on a bench plate. Roger stands on the tower,
// two agents' planes fly in toward the one runway (main), Detente holds both when their changes
// collide, and they land in turn. Roger and the planes are voxels built from the site's own pixel
// art in art/roger.json and art/plane.json.
//
// Drawn with the Anatomy skill's kit (MIT, github.com/wheresryan22/anatomy). Build:
//   node art/figures/tower/build.mjs            writes tower.html next to this file
// The kit is read from ~/.claude/skills/anatomy, or from $ANATOMY.
import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { LOOP, STEPS, stateAt } from "./model.mjs";

// The run's six moments, in order, matching STEPS in model.mjs. The corners name the one showing,
// so a still of the figure reads as one step of a flow.
const STEP_NAMES = ["In the air", "Collision", "You pick B", "lay-claude lands", "a-codex fixes", "Both landed"];
const stepLabel = (index) => `Step ${index + 1} of ${STEP_NAMES.length}`;

const HERE = dirname(fileURLToPath(import.meta.url));
const ART = join(HERE, "..", "..");
const SKILL = process.env.ANATOMY ?? join(homedir(), ".claude", "skills", "anatomy");
const k = await import(pathToFileURL(join(SKILL, "kit", "iso-kit.mjs")).href);
const { kitScript } = await import(pathToFileURL(join(SKILL, "scripts", "inline-kit.mjs")).href);

const ROGER = JSON.parse(readFileSync(join(ART, "roger.json"), "utf8"));
const PLANE = JSON.parse(readFileSync(join(ART, "plane.json"), "utf8"));

const WIDTH = 760;
const HEIGHT = 412;

const BOARD = { x: -182, y: -92, w: 360, d: 150, r: 9 };
const BOARD_H = 12;
const FOOT_H = 5;
const RUNWAY = { x: -112, y: -12, w: 272, d: 38, r: 1 };
const LINE_Y = 7;
const TOWER = { x: -50, y: -76, w: 22, d: 22, r: 1.5 };
const DECK_Z = 58;
const DECK = { x: -74, y: -82, w: 70, d: 34, r: 2 };
const HANGAR = { x: 34, y: -84, w: 78, d: 38, r: 1.5 };
const HANGAR_H = 20;
const APRON = { x: 24, y: -48, w: 98, d: 30, r: 2 };
const ROGER_V = 2.3;
const ROGER_T = 6;
const PLANE_V = 2.5;
const PLANE_T = 9;
const PLANE_LEN = PLANE.width * PLANE_V;

const P = k.fitProjection(
  [...k.boxCorners(BOARD, -BOARD_H - FOOT_H, 0), [-240, 50, 88 + 13 * PLANE_V], [-215, 7, 74 + 13 * PLANE_V], [-240, 50, 0], [DECK.x, DECK.y, DECK_Z + 4 + 24 * ROGER_V + 2]],
  WIDTH,
  HEIGHT,
  { pad: 26, azimuth: 58 },
);

const at = (point) => k.iso(point, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

// One voxel run: the face toward the viewer keeps the pixel's colour, the side and top are shaded.
function box(plan, z, h, colour) {
  const p = k.slabOf(plan, z, h, P, 1);
  const faces = p.shades.map((d, i) => (d ? `<path data-s="${i}" d="${d}"/>` : "")).join("");
  return `<g class="vx" style="--c:${colour}">${faces}<path class="vt" d="${p.top}"/></g>`;
}

// Pixel art standing upright along x, one voxel deep run per row of matching pixels. Rows are laid
// bottom to top and runs far to near, so every face is painted over what it hides.
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

const trimmed = (rows) => {
  let last = rows.length;
  while (last > 0 && !/[^.]/.test(rows[last - 1])) last--;
  return rows.slice(0, last);
};

function roger(mood) {
  const rows = trimmed(ROGER.moods[mood].frames[0]);
  const colours = { ...ROGER.palette, ...ROGER.accent[mood] };
  const wide = rows[0].length * ROGER_V;
  const x = DECK.x + (DECK.w - wide) / 2;
  return voxels(rows, colours, [x, DECK.y + DECK.d / 2 - ROGER_T / 2, DECK_Z + 4], ROGER_V, ROGER_T);
}

// A plane at the origin, nose toward +x, wheels on z 0. The page moves it with translateAlong.
function plane(owner, mood) {
  const rows = trimmed(PLANE.moods[mood].frames[0]);
  return voxels(rows, { ...PLANE.shared, ...PLANE.owners[owner] }, [0, -PLANE_T / 2, 0], PLANE_V, PLANE_T);
}

function board() {
  const out = [`<path class="iso-halo" d="${k.haloOf(BOARD, -BOARD_H - FOOT_H, BOARD_H, P)}"/>`];
  for (const [x, y] of byDepth(k.corners(BOARD, 24))) {
    out.push(S(k.cylinder(x, y, 8, -BOARD_H - FOOT_H, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 6.2, -BOARD_H - FOOT_H + 1.6, FOOT_H - 1.6, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(BOARD, -BOARD_H, BOARD_H, P, 8, 1.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(BOARD, 5), 0, P), { tone: "lo" }));
  const screws = k.corners(BOARD, 11);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.4, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  // A ruler strip along the front edge, ticks every 5, a major every 25.
  const strip = { x: -150, y: BOARD.y + BOARD.d - 14, w: 300, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 5, strip.x + strip.w - 5, 5, 5, strip.y + 0.8, 0.6, [2, 3.8], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  out.push(D([at([strip.x + 2.4, strip.y + 3.5, 0.6]), at([strip.x + strip.w - 2.4, strip.y + 3.5, 0.6])], { size: 0.45 }));
  return out.join("");
}

function runway() {
  const out = [S(k.slabOf(RUNWAY, 0, 0.8, P, 2), { tone: "lo", crease: "none" })];
  const top = 0.8;
  const paint = (plan) => S(k.slabOf(plan, top, 0.2, P, 1), { tone: "faint", crease: "none", flat: true });
  // Threshold bars at both ends, and the centreline dashes between them.
  for (const x0 of [RUNWAY.x + 4, RUNWAY.x + RUNWAY.w - 16]) {
    for (let i = 0; i < 6; i++) out.push(paint({ x: x0, y: RUNWAY.y + 4 + i * 5.2, w: 12, d: 2.6, r: 0 }));
  }
  for (let x = RUNWAY.x + 40; x < RUNWAY.x + RUNWAY.w - 30; x += 22) out.push(paint({ x, y: LINE_Y - 0.6, w: 11, d: 1.2, r: 0 }));
  for (const y of [RUNWAY.y + 5, RUNWAY.y + RUNWAY.d - 7]) out.push(paint({ x: RUNWAY.x + 34, y, w: 16, d: 2, r: 0 }));
  out.push(L(k.planOutline(k.insetPlan(RUNWAY, 1.5), top, P, 2), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([RUNWAY.x + 21, LINE_Y + 2.2], top, P, "x"), "main", { size: 6, tone: "lo", anchor: "middle" }));
  // Edge lights down both sides, end lights across both ends.
  const edges = [];
  for (let x = RUNWAY.x + 6; x <= RUNWAY.x + RUNWAY.w - 6; x += 17) edges.push([x, RUNWAY.y - 2.4], [x, RUNWAY.y + RUNWAY.d + 2.4]);
  out.push(D(byDepth(edges).map(([x, y]) => at([x, y, 0.4])), { size: 0.7, tone: "mid" }));
  const ends = [];
  for (let y = RUNWAY.y + 3; y < RUNWAY.y + RUNWAY.d; y += 6.4) ends.push([RUNWAY.x - 2.4, y], [RUNWAY.x + RUNWAY.w + 2.4, y]);
  out.push(D(ends.map(([x, y]) => at([x, y, 0.4])), { size: 0.6, tone: "hi" }));
  return out.join("");
}

// The approach lights: five posts with a bar of lamps, and the box that switches them.
function approach() {
  const out = [];
  const box = { x: -168, y: -40, w: 16, d: 12, r: 1.4 };
  out.push(S(k.slabOf(box, 0, 9, P, 3, 0.5), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(box, 2), 9, P, 3), { tone: "faint" }));
  out.push(D(k.corners(box, 2.6).map(([x, y]) => at([x, y, 9])), { size: 0.4 }));
  for (let i = 0; i < 5; i++) {
    const x = RUNWAY.x - 12 - i * 11;
    out.push(S(k.cylinder(x, LINE_Y, 1, 0, 6, P, 12), { tone: "mid", crease: "none" }));
    out.push(S(k.slabOf({ x: x - 1.2, y: LINE_Y - 6, w: 2.4, d: 12, r: 0.6 }, 6, 1.4, P, 2), { tone: "mid" }));
    out.push(D([-4, 0, 4].map((dy) => at([x, LINE_Y + dy, 7.4])), { size: 0.55, tone: "hi" }));
  }
  return out.join("");
}

// PAPI: four lamp boxes beside the touchdown zone that tell a pilot if the glide is right.
function papi() {
  const out = [];
  for (let i = 3; i >= 0; i--) {
    const plan = { x: -86, y: RUNWAY.y - 24 + i * 5, w: 5, d: 3.6, r: 0.6 };
    out.push(S(k.slabOf(plan, 0, 2.4, P, 2, 0.3), { tone: "mid" }));
    out.push(D([at([plan.x + plan.w, plan.y + 1.8, 1.4])], { size: 0.5, tone: i < 2 ? "hi" : "mid" }));
  }
  return out.join("");
}

function tower() {
  const out = [];
  const plinth = k.insetPlan(TOWER, -5);
  out.push(`<path class="iso-halo" d="${k.haloOf(plinth, 0, 0.1, P)}" style="filter:blur(5px)"/>`);
  out.push(S(k.slabOf(plinth, 0, 4, P, 4, 0.6), { tone: "mid" }));
  out.push(D(k.corners(plinth, 2.4).map(([x, y]) => at([x, y, 4])), { size: 0.4 }));
  out.push(S(k.slabOf(TOWER, 4, DECK_Z - 4, P, 3, 0.5), { tone: "mid", inner: L([18, 34, 48].map((z) => k.sideSeam(TOWER, z, P, 3)).join(""), { tone: "faint" }) }));
  // A door on the front face, and the cable trench from the plinth to the approach box.
  const door = { x: TOWER.x + 5, y: TOWER.y + TOWER.d, w: 8, d: 0.6, r: 0 };
  out.push(S(k.slabOf(door, 4, 11, P, 1), { tone: "lo", crease: "none" }));
  out.push(D([at([door.x + 6.4, door.y + 0.6, 10])], { size: 0.4 }));
  out.push(S(k.slabOf(k.insetPlan(DECK, 4), DECK_Z - 3, 3, P, 3), { tone: "mid" }));
  out.push(S(k.slabOf(DECK, DECK_Z, 4, P, 4, 0.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(DECK, 3), DECK_Z + 4, P, 4), { tone: "faint" }));
  out.push(D(k.corners(DECK, 2.6).map(([x, y]) => at([x, y, DECK_Z + 4])), { size: 0.45 }));
  return out.join("");
}

// The hold beacon on the deck's front corner: lit red while Detente holds both flights.
const BEACON = [DECK.x + DECK.w - 6, DECK.y + DECK.d - 6];
function beacon() {
  return [
    S(k.cylinder(BEACON[0], BEACON[1], 3.4, DECK_Z + 4, 2, P, 20), { tone: "mid" }),
    `<g data-part="beacon">${S(k.cylinder(BEACON[0], BEACON[1], 2.5, DECK_Z + 6, 5, P, 20), { tone: "hi", crease: "none" })}</g>`,
    S(k.cylinder(BEACON[0], BEACON[1], 3, DECK_Z + 11, 1, P, 20), { tone: "mid" }),
    `<g data-part="glow" style="opacity:0"><circle cx="${at([...BEACON, DECK_Z + 8.5])[0]}" cy="${at([...BEACON, DECK_Z + 8.5])[1]}" r="11" fill="#ff2b3f" style="filter:blur(6px);mix-blend-mode:screen" opacity=".7"/></g>`,
  ].join("");
}

function wire() {
  const from = [TOWER.x - 5, TOWER.y + 4, 0.6];
  const to = [-152, -36, 2];
  return k.wireSvg(at(from), at(to), { via: [at([-120, -66, 0.6]), at([-140, -36, 0.6])], tone: "lo" });
}

// The hangar and its apron behind the runway: corrugated roof, sliding doors toward the runway,
// a window band, and two marked stands with lead-in lines from the runway.
function hangar() {
  const out = [S(k.slabOf(APRON, 0, 0.6, P, 3), { tone: "lo", crease: "none" })];
  const paint = (plan) => S(k.slabOf(plan, 0.6, 0.2, P, 1), { tone: "faint", crease: "none", flat: true });
  for (const x of [52, 94]) {
    out.push(L(k.lineOnTop([x, APRON.y + APRON.d], [x, APRON.y + 9], 0.8, P), { tone: "faint" }));
    out.push(paint({ x: x - 7, y: APRON.y + 7, w: 14, d: 1.4, r: 0 }));
  }
  out.push(L(k.planOutline(k.insetPlan(APRON, 1.5), 0.6, P, 3), { tone: "faint" }));
  out.push(D(byDepth(k.corners(APRON, 3)).map(([x, y]) => at([x, y, 0.6])), { size: 0.4 }));
  const { x, y, w, d } = HANGAR;
  const front = y + d;
  out.push(S(k.slabOf(HANGAR, 0, HANGAR_H, P, 3, 0.4), {
    tone: "mid",
    inner: L([k.sideSeam(HANGAR, 4, P, 3), k.sideSeam(HANGAR, 13, P, 3), k.sideSeam(HANGAR, 16, P, 3)].join(""), { tone: "faint" }),
  }));
  // Window band on the near end: small panes between the two seams.
  const panes = [];
  for (let py = y + 5; py < front - 4; py += 5) panes.push(at([x + w, py, 14.5]));
  out.push(D(panes, { size: 0.5, tone: "lo" }));
  // Sliding doors on the side facing the runway, in four leaves on a track.
  const door = { x: x + 7, y: front, w: w - 14, d: 0.8, r: 0 };
  out.push(S(k.slabOf(door, 0, 12.5, P, 1), { tone: "lo", crease: "none" }));
  const leaves = [];
  for (let i = 1; i < 4; i++) leaves.push(k.rise([door.x + (door.w * i) / 4, front + 0.8], 0.4, 12, P));
  out.push(L(leaves.join(""), { tone: "mid" }));
  out.push(L(k.segment([door.x - 2, front + 0.9, 13.2], [door.x + door.w + 2, front + 0.9, 13.2], P), { tone: "mid" }));
  out.push(D([0.5, 1.5, 2.5, 3.5].map((i) => at([door.x + (door.w * i) / 4, front + 0.8, 6.5])), { size: 0.35 }));
  // Corrugated roof with an overhang, ribs running front to back.
  const roof = k.insetPlan(HANGAR, -2);
  out.push(S(k.slabOf(roof, HANGAR_H, 2, P, 3, 0.4), { tone: "mid" }));
  const ribs = [];
  for (let rx = roof.x + 4; rx < roof.x + roof.w - 2; rx += 4) ribs.push(k.lineOnTop([rx, roof.y + 1.5], [rx, roof.y + roof.d - 1.5], HANGAR_H + 2, P));
  out.push(L(ribs.join(""), { tone: "faint" }));
  out.push(D(k.corners(roof, 2.2).map(([cx, cy]) => at([cx, cy, HANGAR_H + 2])), { size: 0.4 }));
  // A roof vent and a lamp over the doors.
  out.push(S(k.cylinder(x + w - 14, y + 10, 2.4, HANGAR_H + 2, 3, P, 16), { tone: "mid" }));
  out.push(L(k.ring(x + w - 14, y + 10, 1.4, HANGAR_H + 5, P, 14), { tone: "lo" }));
  return out.join("");
}

const WINDSOCK = [140, -56];
function windsock() {
  const [x, y] = WINDSOCK;
  const out = [S(k.slabOf({ x: x - 4, y: y - 4, w: 8, d: 8, r: 1 }, 0, 2, P, 2, 0.3), { tone: "mid" })];
  out.push(S(k.cylinder(x, y, 0.8, 2, 26, P, 10), { tone: "mid", crease: "none" }));
  const sock = ["KRRWWRRK.", "KRRWWRRWK", "KRRWWRRK."];
  out.push(voxels(sock, { K: "#000000", R: "#ff6b62", W: "#ffffff" }, [x + 0.8, y - 1, 22], 1.6, 2));
  return out.join("");
}

function shadow(name) {
  const plan = { x: 4, y: -PLANE_T / 2 - 4, w: PLANE_LEN - 8, d: PLANE_T + 8, r: 8 };
  return `<g data-part="${name}-shadow"><path class="iso-halo" d="${k.haloOf(plan, 0, 0.1, P)}" style="filter:blur(4px)"/></g>`;
}

const MOODS = ["cleared", "worried", "happy"];
function flightGroup(name, owner) {
  return `<g data-part="${name}">${MOODS.map((mood) => `<g data-mood="${mood}"${mood === "cleared" ? "" : ' style="display:none"'}>${plane(owner, mood)}</g>`).join("")}</g>`;
}

const ROGER_MOODS = ["watching", "collision", "resolved"];
const first = stateAt(0);
const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label:
    "An airfield model on a bench plate. Roger stands on the tower. Two agents' planes, lay-claude in blue and a-codex in orange, fly in toward one runway marked main. When their changes collide, Roger turns red, the beacon lights and both planes hold in the air. After the person picks a fix, lay-claude lands, then a-codex lands once it has updated its call.",
  body: [
    board(),
    runway(),
    approach(),
    papi(),
    wire(),
    shadow("a"),
    shadow("b"),
    tower(),
    hangar(),
    windsock(),
    `<g data-part="roger">${ROGER_MOODS.map((mood) => `<g data-mood="${mood}"${mood === "watching" ? "" : ' style="display:none"'}>${roger(mood)}</g>`).join("")}</g>`,
    beacon(),
    `<g data-part="flights">${flightGroup("b", "a")}${flightGroup("a", "lay")}</g>`,
  ],
});

const strip = (source) => source.replace(/^export /gm, "");
const live = `
${strip(readFileSync(join(HERE, "model.mjs"), "utf8"))}
const P = ${JSON.stringify(P)};
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const part = (name) => svg.querySelector('[data-part="' + name + '"]');
const flights = part("flights");
const groups = { a: part("a"), b: part("b") };
const shadows = { a: part("a-shadow"), b: part("b-shadow") };
const rogerGroup = part("roger");
const beaconLight = part("beacon").firstElementChild;
const glow = part("glow");
const readout = document.querySelector("[data-readout]");
const STEP_NAMES = ${JSON.stringify(STEP_NAMES)};
const stepCorner = document.querySelector('[data-corner="fig"]');
const nameCorner = document.querySelector('[data-corner="title"]');
const still = matchMedia("(prefers-reduced-motion: reduce)");
const HOLD_POSE = 5.6;
let clock = still.matches ? HOLD_POSE : 0, touring = !still.matches, visible = false, frame = 0, last = 0, target = clock;
const scrub = document.querySelector(".tw-scrub");
const playButton = document.querySelector('[data-act="play"]');
const stepButtons = [...document.querySelectorAll("[data-step]")];
const END = LOOP - 0.7;
const stepAt = (time) => STEPS.reduce((best, step, index) => (step <= time + 0.01 ? index : best), 0);
// A link can open the figure at one moment, e.g. tower.html#t=10.
const pinned = /t=([0-9.]+)/.exec(location.hash);
if (pinned) { clock = target = Math.min(LOOP, +pinned[1]); touring = false; }
// tower.html#t=5.6&still draws the card alone, for the README picture.
if (/still/.test(location.hash)) document.documentElement.classList.add("is-still");
const showMood = (group, mood) => { for (const child of group.children) child.style.display = child.dataset.mood === mood ? "" : "none"; };
function draw() {
  const s = stateAt(clock);
  for (const name of ["a", "b"]) {
    const f = s[name];
    groups[name].setAttribute("transform", translateAlong(P, [f.x, f.y, f.z]));
    groups[name].style.opacity = s.fade.toFixed(3);
    showMood(groups[name], f.mood);
    shadows[name].setAttribute("transform", translateAlong(P, [f.x, f.y, 0]));
    shadows[name].style.opacity = (s.fade * Math.max(0.15, 0.85 - f.z / 90)).toFixed(3);
  }
  const nearA = depthOf([s.a.x, s.a.y, s.a.z], P) > depthOf([s.b.x, s.b.y, s.b.z], P);
  if ((flights.lastElementChild === groups.a) !== nearA) flights.appendChild(nearA ? groups.a : groups.b);
  showMood(rogerGroup, s.roger);
  beaconLight.toggleAttribute("data-lit", s.beacon);
  beaconLight.classList.toggle("is-hold", s.beacon);
  glow.style.opacity = s.beacon ? "1" : "0";
  if (readout.textContent !== s.readout) readout.textContent = s.readout;
  scrub.value = Math.min(END, s.t).toFixed(2);
  scrub.style.setProperty("--p", (Math.min(END, s.t) / END * 100).toFixed(2) + "%");
  scrub.setAttribute("aria-valuetext", s.readout);
  const here = stepAt(s.t);
  stepButtons.forEach((button, index) => button.toggleAttribute("aria-current", index === here));
  if (stepCorner.dataset.step !== String(here)) {
    stepCorner.dataset.step = String(here);
    stepCorner.textContent = "Step " + (here + 1) + " of " + STEP_NAMES.length;
    nameCorner.textContent = STEP_NAMES[here];
  }
}
const showPlaying = () => {
  playButton.textContent = touring ? "Pause" : "Play";
  playButton.setAttribute("aria-label", touring ? "Pause the run" : "Play the run");
};
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 20) : 1 / 60;
  last = now;
  if (touring) clock = (clock + dt) % LOOP;
  else clock += (target - clock) * (1 - Math.exp(-dt / 0.18));
  draw();
  const settled = !touring && Math.abs(target - clock) < 0.001;
  if (settled) clock = target;
  frame = visible && !settled ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
// Any touch of the controls pauses the run where the person put it, until they press Play.
const steer = (to) => {
  touring = false;
  target = Math.min(END, Math.max(0, to));
  showPlaying();
  run();
};
const step = (by) => steer(STEPS[Math.min(STEPS.length - 1, Math.max(0, stepAt(target) + by))] + 0.3);
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
// Tap or click the drawing for the next step; drag across it to scrub. Vertical swipes still scroll.
let press = null;
stage.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  press = { x: event.clientX, from: touring ? clock : target, dragging: false };
});
stage.addEventListener("pointermove", (event) => {
  if (!press) return;
  const dx = event.clientX - press.x;
  if (!press.dragging && Math.abs(dx) > 8) { press.dragging = true; stage.setPointerCapture(event.pointerId); stage.classList.add("is-dragging"); }
  if (press.dragging) steer(press.from + (dx / svg.getBoundingClientRect().width) * END);
});
const release = (event) => {
  if (!press) return;
  if (!press.dragging && event.type === "pointerup") {
    if (target >= STEPS[STEPS.length - 1] && !touring) steer(0); else { if (touring) target = clock; step(1); }
  }
  press = null;
  stage.classList.remove("is-dragging");
};
stage.addEventListener("pointerup", release);
stage.addEventListener("pointercancel", release);
scrub.addEventListener("input", () => steer(+scrub.value));
stepButtons.forEach((button) => button.addEventListener("click", () => steer(STEPS[+button.dataset.step] + 0.3)));
document.querySelector('[data-act="back"]').addEventListener("click", () => { if (touring) target = clock; step(-1); });
document.querySelector('[data-act="next"]').addEventListener("click", () => { if (touring) target = clock; step(1); });
playButton.addEventListener("click", () => {
  touring = !touring;
  if (touring && target >= END - 0.05) clock = 0;
  if (!touring) target = clock;
  showPlaying();
  run();
});
stage.addEventListener("keydown", (event) => {
  let to = null;
  if (event.key === "ArrowRight" || event.key === "ArrowUp") to = STEPS[Math.min(STEPS.length - 1, stepAt(target) + 1)] + 0.3;
  if (event.key === "ArrowLeft" || event.key === "ArrowDown") to = STEPS[Math.max(0, stepAt(target) - 1)] + 0.3;
  if (event.key === "Home") to = 0;
  if (event.key === "End") to = STEPS[STEPS.length - 1] + 1.6;
  if (event.key === " " || event.key === "Enter") { event.preventDefault(); playButton.click(); return; }
  if (to === null) return;
  event.preventDefault();
  if (touring) target = clock;
  steer(to);
});
showPlaying();
draw();
`;

const CSS = `
.vx path{stroke-width:.5px;stroke-linejoin:round}
.vx>[data-s="3"]{fill:var(--c);stroke:var(--c)}
.vx>[data-s="2"]{fill:color-mix(in srgb,var(--c),#000 18%);stroke:color-mix(in srgb,var(--c),#000 18%)}
.vx>[data-s="1"]{fill:color-mix(in srgb,var(--c),#000 34%);stroke:color-mix(in srgb,var(--c),#000 34%)}
.vx>[data-s="0"]{fill:color-mix(in srgb,var(--c),#000 48%);stroke:color-mix(in srgb,var(--c),#000 48%)}
.vx>.vt{fill:color-mix(in srgb,var(--c),#fff 16%);stroke:color-mix(in srgb,var(--c),#fff 16%)}
.iso-solid.is-hold>.iso-top,.iso-solid.is-hold>.iso-shade,.iso-solid.is-hold>.iso-fill{fill:#ff2b3f}
.iso-solid.is-hold>.iso-edge{stroke:#ff8f8f}
.is-still body{background:transparent}.is-still .iso-plate{box-shadow:none}.is-still .iso-page{margin:0;width:820px}.is-still .iso-legend,.is-still [data-corner="hint"]{display:none}
.iso{--anatomy-mono:"Geist Mono",ui-monospace,Menlo,monospace}
.iso-stage{cursor:pointer;touch-action:pan-y;-webkit-tap-highlight-color:transparent;user-select:none;-webkit-user-select:none}
.iso-stage.is-dragging{cursor:grabbing}
.iso-stage:focus-visible,.tw-controls button:focus-visible,.tw-scrub:focus-visible{outline:2px solid var(--anatomy-strong);outline-offset:3px}
.tw-controls{display:grid;gap:14px;margin-top:28px;font-family:var(--anatomy-mono)}
.tw-row{display:flex;gap:8px;align-items:center}
.tw-controls button{min-height:44px;padding:0 16px;border:0;border-radius:0;background:var(--anatomy-face);color:var(--anatomy-strong);font:inherit;font-size:13px;cursor:pointer;box-shadow:0 0 0 1px var(--anatomy-lo);touch-action:manipulation;transition:background-color .15s,color .15s}
.tw-controls button:hover{background:var(--anatomy-lit-top)}
.tw-controls button:active{transform:translateY(1px)}
.tw-controls [data-act="play"]{min-width:84px;background:var(--anatomy-strong);color:var(--anatomy-card);box-shadow:none}
.tw-controls [data-act="play"]:hover{background:var(--anatomy-lit)}
.tw-scrub{flex:1;min-width:0;height:44px;margin:0;background:transparent;-webkit-appearance:none;appearance:none;cursor:pointer;touch-action:pan-y}
.tw-scrub::-webkit-slider-runnable-track{height:4px;background:linear-gradient(90deg,var(--anatomy-strong) var(--p,0%),var(--anatomy-lo) var(--p,0%))}
.tw-scrub::-moz-range-track{height:4px;background:linear-gradient(90deg,var(--anatomy-strong) var(--p,0%),var(--anatomy-lo) var(--p,0%))}
.tw-scrub::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;margin-top:-9px;border-radius:50%;background:var(--anatomy-strong);box-shadow:0 0 0 4px var(--anatomy-card)}
.tw-scrub::-moz-range-thumb{width:22px;height:22px;border:0;border-radius:50%;background:var(--anatomy-strong);box-shadow:0 0 0 4px var(--anatomy-card)}
.tw-steps{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:0;padding:0;list-style:none}
.tw-steps li{display:flex}.tw-steps button{width:100%;height:100%;padding:8px 8px;text-align:left;line-height:1.3;color:var(--anatomy-text)}
.tw-steps button span{display:block;color:var(--anatomy-muted);font-size:11px}
.tw-steps button[aria-current]{background:var(--anatomy-strong);color:var(--anatomy-card);box-shadow:none}
.tw-steps button[aria-current] span{color:inherit;opacity:.7}
.tw-steps li:nth-child(2) button[aria-current]{background:#ff2b3f;color:#fff}
@media (max-width:640px){.iso-plate{padding:44px 12px 64px}.tw-steps{grid-template-columns:repeat(3,1fr)}.tw-row .tw-skip{display:none}}
.is-still .tw-controls{display:none}
`;

function controls() {
  const steps = STEP_NAMES.map((name, index) => `<li><button type="button" data-step="${index}"><span>${index + 1}</span>${name}</button></li>`).join("");
  return `<div class="tw-controls">
<div class="tw-row"><button type="button" data-act="play">Pause</button><button type="button" class="tw-skip" data-act="back" aria-label="Previous step">Back</button><input class="tw-scrub" type="range" min="0" max="${LOOP - 0.7}" step="0.01" value="0" aria-label="Scrub through the run"><button type="button" class="tw-skip" data-act="next" aria-label="Next step">Next</button></div>
<ol class="tw-steps" aria-label="Jump to a moment">${steps}</ol>
</div>`;
}

const body = k.plateHtml({
  fig: stepLabel(0),
  title: STEP_NAMES[0],
  hint: "Tap for the next step, drag to scrub",
  readout: first.readout,
  keys: [
    { mark: "lit", label: "The hold beacon: lit while Detente holds both flights" },
    { mark: "raised", label: "Roger and the planes, built from the site's own pixel art" },
  ],
  caption:
    "Two agents are in the air with unpushed work, heading for one runway: main. lay-claude changed create_session(user) to create_session(user, ttl); a-codex still calls it the old way. No lines overlap, yet Detente holds both before either lands. You pick B: lay-claude lands as it is, a-codex updates its call and lands after.",
  body: `<div class="iso-stage" tabindex="0" role="group" aria-label="The tower. Tap or press the right arrow for the next step, drag to scrub, space to play or pause.">${svg}</div>${controls()}`,
});

const page = k.pageHtml({ title: "The tower", theme: "dark", body, script: kitScript() + live, width: 820 }).replace("</style>", `${CSS}</style>`);
writeFileSync(join(HERE, "tower.html"), page);
console.log("wrote tower.html", Math.round(page.length / 1024), "KB");
