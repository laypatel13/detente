import { type Mood, PLANE_NAME, type RadarState } from "@/lib/radar";
import recordingA from "./recordings/a.json";
import recordingB from "./recordings/b.json";

export type Choice = "A" | "B";
export type Frame = { at: number; state: RadarState };

const CALLSIGNS: [string, string][] = [
  ["lay-claude", PLANE_NAME.lay],
  ["a-codex", PLANE_NAME.a],
  ["b-opencode", PLANE_NAME.b],
];

// The recordings keep the real callsigns. The showcase shows each agent by its plane's name.
function named(frames: unknown) {
  let text = JSON.stringify(frames);
  for (const [callsign, name] of CALLSIGNS) text = text.replaceAll(callsign, name);
  return JSON.parse(text) as Frame[];
}

const FRAMES: Record<Choice, Frame[]> = {
  A: named(recordingA.frames),
  B: named(recordingB.frames),
};

function decidedAt(frames: Frame[]) {
  return frames.findIndex(({ state }) =>
    state.conflicts.some((conflict) => conflict.status === "decided"),
  );
}

// Both recordings are the same flight until a person picks, then each is its own real run.
const SHARED = FRAMES.A.slice(0, decidedAt(FRAMES.A));

export function timeline(choice: Choice | null) {
  if (!choice) return SHARED;
  return [...SHARED, ...FRAMES[choice].slice(decidedAt(FRAMES[choice]))];
}

function said(state: RadarState, tag: string) {
  return state.feed.some((message) => message.tag === tag);
}

export type Stop = {
  reached: (state: RadarState) => boolean;
  watching: string;
  mood: Mood;
  title: string;
  text: string | Record<Choice, string>;
  forReal: string;
  action: { kind: "next"; label: string } | { kind: "pick"; label: string } | { kind: "end" };
};

export const STOPS: Stop[] = [
  {
    reached: () => true,
    watching: "",
    mood: "watching",
    title: "You're on duty",
    text: "Evening. I'm Roger, and I run this tower. Three coding agents on three laptops are about to work on one project. They can't see each other's code. I can, and you're the person I answer to.",
    forReal:
      "A small program on each laptop tells your team's own Detente what its agent is changing.",
    action: { kind: "next", label: "Start the shift" },
  },
  {
    reached: (state) => said(state, "TRAFFIC"),
    watching: "The agents are filing flight plans.",
    mood: "traffic",
    title: "Traffic",
    text: "Heads up. Every agent told me what it plans to edit before touching code. Mayday plans to use create_session, and Wilco is changing it. Nothing's broken yet, so this is only a warning.",
    forReal: "Agents post flight plans in your team's chat, and a hook refuses edits without one.",
    action: { kind: "next", label: "Let them write code" },
  },
  {
    reached: (state) =>
      said(state, "DECISION") && state.conflicts.some((conflict) => conflict.status === "open"),
    watching: "The agents are writing code on their own laptops.",
    mood: "collision",
    title: "Collision!",
    text: "Wilco added a required argument, and Mayday's unpushed code still calls it the old way. Different files, no overlapping lines, nothing pushed. I've held both flights. Your call.",
    forReal: "Held agents can't edit or commit until a person decides.",
    action: { kind: "pick", label: "See what broke" },
  },
  {
    reached: (state) => said(state, "RESOLVED"),
    watching: "The agent you picked is making the fix.",
    mood: "resolved",
    title: "The code fits again",
    text: {
      A: "Wilco gave ttl a default, so the old call works. I read the code again, saw the break was gone and closed the conflict room.",
      B: "Mayday updated its call in refunds.py. I read the code again, saw the break was gone and closed the conflict room.",
    },
    forReal: "You'd reply A or B in your team's chat. Then the agent makes the edit.",
    action: { kind: "next", label: "Land the flights" },
  },
  {
    reached: (state) => state.mood === "resolved",
    watching: "The flights are landing.",
    mood: "resolved",
    title: "All flights down",
    text: "Good shift. Nothing broke, and nothing reached a pull request. Everything you watched was recorded from a real run on Switch, including the fix you picked.",
    forReal: "Set it up on your project and this radar shows your own team's agents.",
    action: { kind: "end" },
  },
];

export const PICK_STOP = STOPS.findIndex((stop) => stop.action.kind === "pick");
