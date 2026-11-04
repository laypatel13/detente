import type { Flight, RadarState } from "@/lib/radar";

const FLIGHTS: Flight[] = [
  { callsign: "Wilco", owner: "lay", task: "", files: [], sector: "auth", status: "cleared" },
  { callsign: "Mayday", owner: "a", task: "", files: [], sector: "billing", status: "cleared" },
  { callsign: "Squawk", owner: "b", task: "", files: [], sector: "cart", status: "cleared" },
];

const FRAME: RadarState = {
  version: 0,
  mood: "watching",
  headline: "",
  crew: [],
  flights: FLIGHTS,
  links: [],
  feed: [],
  conflicts: [],
};

const WORRIED = new Set(["Wilco", "Mayday"]);

// The landing page's picture of a collision. Only the landing page may use it.
export const HERO_FRAMES: RadarState[] = [
  { ...FRAME, headline: "Three flights cleared. Three laptops, one project." },
  {
    ...FRAME,
    mood: "traffic",
    headline: "Mayday uses create_session, which Wilco is changing.",
    links: [{ kind: "traffic", from: "Mayday", to: "Wilco", reason: "" }],
  },
  {
    ...FRAME,
    mood: "collision",
    headline: "billing/refunds.py:5 is missing required argument ttl.",
    flights: FLIGHTS.map((flight) =>
      WORRIED.has(flight.callsign) ? { ...flight, status: "worried" } : flight,
    ),
    links: [{ kind: "collision", from: "Wilco", to: "Mayday", reason: "" }],
  },
];
