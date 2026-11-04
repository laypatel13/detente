import plane from "@/lib/art/plane.json";

export type Mood = "watching" | "traffic" | "collision" | "resolved" | "stop" | "resting";
export type FlightStatus = "cleared" | "hold" | "worried" | "landed";
export type CrewStatus = FlightStatus | "parked";
export type Owner = "lay" | "a" | "b" | "c" | "d" | "e" | "f" | "g";

export type Flight = {
  callsign: string;
  owner: Owner;
  task: string;
  files: string[];
  sector: string;
  status: FlightStatus;
};

export type CrewMember = {
  person: string;
  owner: Owner;
  callsign: string;
  vendor: string;
};

export type Link = {
  kind: "traffic" | "collision";
  from: string;
  to: string;
  reason: string;
};

export type FeedMessage = {
  id: number;
  room: string;
  sender: string;
  tag: string | null;
  face: string | null;
  text: string;
};

export type Conflict = {
  id: string;
  kind: "contract" | "same_function" | "same_file" | "same_lines";
  symbol: string;
  status: "open" | "decided" | "resolved";
  reason: string;
  before: string | null;
  after: string | null;
  changed_by: string;
  changed_file: string;
  caller: string;
  breaks: { file: string; line: number; code: string };
  options: { key: string; text: string; agent: string }[];
  decision: { by: string; option: string } | null;
};

export type RadarState = {
  version: number;
  mood: Mood;
  headline: string;
  crew: CrewMember[];
  flights: Flight[];
  links: Link[];
  feed: FeedMessage[];
  conflicts: Conflict[];
};

export const PLANE_NAME = plane.names as Record<Owner, string>;

// Line 0 means the whole function or file, so it isn't shown.
export function conflictLocation({ breaks }: Conflict) {
  return breaks.line ? `${breaks.file}:${breaks.line}` : breaks.file;
}

// A broken call names the line it breaks; the other kinds already say where in the reason.
export function conflictHeadline(conflict: Conflict) {
  return conflict.kind === "contract"
    ? `${conflictLocation(conflict)} ${conflict.reason}`
    : conflict.reason;
}

export const STATUS_LABEL: Record<CrewStatus, string> = {
  cleared: "Cleared",
  hold: "Holding",
  worried: "Collision course",
  landed: "Landed",
  parked: "Parked",
};

export type SignKind = "hold" | "traffic" | "cleared" | "plain";

export const STATUS_SIGN: Record<CrewStatus, SignKind> = {
  cleared: "cleared",
  hold: "hold",
  worried: "hold",
  landed: "plain",
  parked: "plain",
};

export const TAG_SIGN: Record<string, SignKind> = {
  CLEARED: "cleared",
  TRAFFIC: "traffic",
  COLLISION: "hold",
  VIOLATION: "traffic",
  DECISION: "traffic",
  DECIDED: "cleared",
  RESOLVED: "cleared",
  "GROUND STOP": "hold",
  RESUME: "cleared",
  LANDED: "plain",
  "FLIGHT PLAN": "plain",
};

export const MOOD_SIGN: Record<Mood, SignKind> = {
  watching: "cleared",
  traffic: "traffic",
  collision: "hold",
  resolved: "cleared",
  stop: "hold",
  resting: "cleared",
};

export const FACE: Record<Mood, string> = {
  watching: "[o_o]",
  traffic: "[¬_¬]",
  collision: "[O_O]!",
  resolved: "[^_^]",
  stop: "[ò_ó]",
  resting: "[-_-]z",
};
