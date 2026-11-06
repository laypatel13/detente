// The story the tower figure tells, as one pure function of time. The build draws its first pose
// from it and the page inlines it, so the planes, Roger and the readout always agree.
//
// It follows the showcase run: lay-claude changes create_session(user) to create_session(user, ttl)
// while a-codex writes code that calls it the old way. Both are in the air (unpushed work) and
// heading for the one runway, main. Detente sees the collision and holds both. The person picks B:
// lay-claude lands as it is, a-codex updates its call, then a-codex lands too.

export const LOOP = 16;
export const STEPS = [0, 4, 7.5, 9, 10.6, 12.9];

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const ease = (v) => { const s = clamp01(v); return s * s * (3 - 2 * s); };
const out = (v) => 1 - (1 - clamp01(v)) ** 3;
const mix = (a, b, s) => a + (b - a) * s;
const span = (t, from, to) => (t - from) / (to - from);

// Where each flight is: approach, hold (bobbing), glide to touchdown at x -80, roll out.
function flight(t, plan) {
  const { start, hold, cleared, touch, rest, phase } = plan;
  let x, y, z;
  if (t < 4) {
    const s = ease(span(t, 0, 4));
    [x, y, z] = [mix(start[0], hold[0], s), mix(start[1], hold[1], s), mix(start[2], hold[2], s)];
  } else if (t < cleared) {
    [x, y, z] = [hold[0], hold[1], hold[2] + Math.sin((t - 4) * 3.4 + phase) * 1.4];
  } else if (t < touch) {
    const settle = hold[2] + Math.sin((cleared - 4) * 3.4 + phase) * 1.4;
    const lineUp = ease(span(t, cleared, cleared + 0.8));
    const glide = span(t, cleared, touch);
    x = mix(hold[0], -80, glide);
    y = mix(hold[1], 7, lineUp);
    z = mix(settle, 0, out(glide) * 0.35 + glide * 0.65);
  } else {
    x = mix(-80, rest, out(span(t, touch, touch + 1.6)));
    [y, z] = [7, 0];
  }
  const landed = t >= touch;
  const holding = t >= 4 && t < cleared;
  const mood = landed ? "happy" : holding ? "worried" : "cleared";
  return { x, y, z, landed, holding, mood };
}

const A = { start: [-215, 7, 74], hold: [-152, 7, 62], cleared: 7.5, touch: 9, rest: 95, phase: 0 };
const B = { start: [-240, 50, 88], hold: [-180, 50, 76], cleared: 10.6, touch: 12.9, rest: 22, phase: 1.9 };

export function stateAt(time) {
  const t = ((time % LOOP) + LOOP) % LOOP;
  const a = flight(t, A);
  const b = flight(t, B);
  const fade = t < 0.6 ? t / 0.6 : t > 15.4 ? (LOOP - t) / 0.6 : 1;
  const inAir = [a, b].filter((f) => !f.landed).length;
  const holding = [a, b].filter((f) => f.holding).length;
  let readout;
  if (t < 4) readout = `${inAir} in the air · 0 holding`;
  else if (t < 7.5) readout = `collision course · ${holding} holding`;
  else if (t < 9) readout = "you picked B · lay-claude cleared";
  else if (t < 10.6) readout = `lay-claude landed · ${holding} holding`;
  else if (t < 12.9) readout = "a-codex fixed its call · cleared";
  else readout = "both landed · 0 open conflicts";
  const roger = t >= 4 && t < 7.5 ? "collision" : t >= 12.9 ? "resolved" : "watching";
  return { t, a, b, fade, roger, beacon: t >= 4 && t < 7.5, readout };
}
