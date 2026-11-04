import type { Flight, Link } from "@/lib/radar";

export const VIEW = 720;
export const ROAD = 30;

const CENTER = VIEW / 2;
const LABEL = 34;
const PAD = 10;
const MOST_APRONS = 12;
const REST = "other";
const MARK_CLEARANCE = 54;

// Clockwise turn of the first apron, so the field stays balanced at each count.
const FIRST_APRON: Record<number, number> = { 4: 315, 6: 30, 10: 18, 12: 15 };
const THREE_APRONS = [315, 45, 180];

export type Point = { x: number; y: number };
export type ApronAlert = "clear" | "traffic" | "hold";

export type Apron = {
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  alert: ApronAlert;
  gate: Point;
  gateOn: "top" | "bottom" | "left" | "right";
  angle: number;
  ringPoint: Point;
  bend: Point;
};

export type Stand = Point & {
  flight: Flight;
  apron: Apron;
  width: number;
  height: number;
  flip: boolean;
};

export type Route = {
  key: string;
  kind: Link["kind"];
  path: string;
  mark: Point;
};

export type Airfield = {
  ringRadius: number;
  aprons: Apron[];
  stands: Stand[];
  routes: Route[];
};

// Rounded so the server and the browser draw the exact same path.
const round = (value: number) => Math.round(value * 100) / 100;

function polar(degrees: number, radius: number): Point {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: round(CENTER + radius * Math.sin(radians)),
    y: round(CENTER - radius * Math.cos(radians)),
  };
}

// More folders means smaller aprons, pushed nearer the edge.
function fieldFor(count: number) {
  if (count <= 2) return { width: 680, height: 216, reach: 236, ringRadius: 108 };
  if (count <= 4) return { width: 250, height: 210, reach: 232, ringRadius: 100 };
  if (count <= 8) return { width: 196, height: 180, reach: 250, ringRadius: 90 };
  return { width: 140, height: 130, reach: 272, ringRadius: 108 };
}

// Each top-level folder with a flight in it gets one apron, however big the team.
function sectorOf(flights: Flight[]) {
  const names = [...new Set(flights.map((flight) => flight.sector))].sort();
  const kept = names.length > MOST_APRONS ? names.slice(0, MOST_APRONS - 1) : names;
  return {
    names: kept.length < names.length ? [...kept, REST] : kept,
    of: (flight: Flight) => (kept.includes(flight.sector) ? flight.sector : REST),
  };
}

function apronsFor(names: string[], alertOf: (name: string) => ApronAlert): Apron[] {
  const { width, height, reach, ringRadius } = fieldFor(names.length);
  const first = FIRST_APRON[names.length] ?? 0;

  return names.map((name, index) => {
    const degrees =
      names.length === 3 ? THREE_APRONS[index] : first + (index * 360) / names.length;
    const turn = (degrees * Math.PI) / 180;
    const across = Math.sin(turn);
    const along = -Math.cos(turn);
    // Pushing the circle out to a square fills the corners of the field.
    const push = reach / Math.max(Math.abs(across), Math.abs(along));
    const middle = { x: CENTER + across * push, y: CENTER + along * push };

    const faces = Math.abs(along) >= Math.abs(across) - 0.01;
    const gateOn = faces
      ? along < 0 ? "bottom" : "top"
      : across < 0 ? "right" : "left";
    const gate = {
      x: round(faces ? middle.x : middle.x - (Math.sign(across) * width) / 2),
      y: round(faces ? middle.y - (Math.sign(along) * height) / 2 : middle.y),
    };

    const angle = (Math.atan2(gate.x - CENTER, CENTER - gate.y) * 180) / Math.PI;
    const ringPoint = polar(angle, ringRadius);
    const bend = faces ? { x: gate.x, y: ringPoint.y } : { x: ringPoint.x, y: gate.y };

    return {
      name,
      x: round(middle.x - width / 2),
      y: round(middle.y - height / 2),
      width,
      height,
      alert: alertOf(name),
      gate,
      gateOn,
      angle,
      ringPoint,
      bend,
    };
  });
}

function standsOn(apron: Apron, flights: Flight[]): Stand[] {
  const room = { width: apron.width - PAD * 2, height: apron.height - LABEL - PAD };
  // A stand is wider than it is tall, so crowded aprons fill sideways first.
  const columns = Math.min(
    flights.length,
    Math.round(Math.sqrt((flights.length * room.width) / (room.height * 1.4))) || 1,
  );
  const rows = Math.ceil(flights.length / columns);
  const width = room.width / columns;
  const height = room.height / rows;

  return flights.map((flight, index) => {
    const x = apron.x + PAD + (index % columns) * width + width / 2;
    const y = apron.y + LABEL + Math.floor(index / columns) * height + height / 2;
    return {
      flight,
      apron,
      x: round(x),
      y: round(y),
      width: round(width),
      height: round(height),
      flip: x > CENTER,
    };
  });
}

function routeBetween(from: Stand, to: Stand, ringRadius: number, link: Link): Route {
  const key = `${link.kind}-${link.from}-${link.to}`;
  const a = from.apron;
  const b = to.apron;
  if (a === b) {
    return {
      key,
      kind: link.kind,
      path: `M${from.x} ${from.y}L${to.x} ${to.y}`,
      mark: { x: round((from.x + to.x) / 2), y: round((from.y + to.y) / 2) },
    };
  }

  // Planes take the taxiways: out one gate, round the ring the short way, in the other.
  const turn = (b.angle - a.angle + 360) % 360;
  const clockwise = turn <= 180;
  const middle = a.angle + (clockwise ? turn : turn - 360) / 2;
  return {
    key,
    kind: link.kind,
    path:
      `M${from.x} ${from.y}L${a.gate.x} ${a.gate.y}` +
      `Q${a.bend.x} ${a.bend.y} ${a.ringPoint.x} ${a.ringPoint.y}` +
      `A${ringRadius} ${ringRadius} 0 0 ${clockwise ? 1 : 0} ${b.ringPoint.x} ${b.ringPoint.y}` +
      `Q${b.bend.x} ${b.bend.y} ${b.gate.x} ${b.gate.y}L${to.x} ${to.y}`,
    mark: polar(middle, ringRadius + MARK_CLEARANCE),
  };
}

export function layoutField(flights: Flight[], links: Link[]): Airfield {
  const sectors = sectorOf(flights);
  const callsignsIn = (name: string) =>
    flights.filter((flight) => sectors.of(flight) === name).map((flight) => flight.callsign);

  const alertOf = (name: string): ApronAlert => {
    const here = callsignsIn(name);
    const held = flights.some(
      (flight) =>
        here.includes(flight.callsign) &&
        (flight.status === "worried" || flight.status === "hold"),
    );
    if (held) return "hold";
    const crossed = links.some((link) => here.includes(link.from) || here.includes(link.to));
    return crossed ? "traffic" : "clear";
  };

  const aprons = apronsFor(sectors.names, alertOf);
  const { ringRadius } = fieldFor(aprons.length);
  const stands = aprons.flatMap((apron) =>
    standsOn(
      apron,
      flights.filter((flight) => sectors.of(flight) === apron.name),
    ),
  );

  const routes = links.flatMap((link) => {
    const from = stands.find((stand) => stand.flight.callsign === link.from);
    const to = stands.find((stand) => stand.flight.callsign === link.to);
    return from && to ? [routeBetween(from, to, ringRadius, link)] : [];
  });

  return { ringRadius, aprons, stands, routes };
}
