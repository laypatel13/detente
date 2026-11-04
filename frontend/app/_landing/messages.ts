import type { FeedMessage } from "@/lib/radar";

// From a real run on Switch, with each agent shown by its plane's name.
export const FLIGHT_PLAN: FeedMessage = {
  id: 1,
  room: "tower",
  sender: "Wilco",
  tag: "FLIGHT PLAN",
  face: null,
  text: "FLIGHT PLAN\ntask: session expiry\nedit: auth/session.py\nchanges: auth.session.create_session",
};

export const CLEARED: FeedMessage = {
  id: 2,
  room: "tower",
  sender: "Detente",
  tag: "CLEARED",
  face: "[o_o]",
  text: "Wilco · auth/session.py",
};

export const USES: FeedMessage = {
  id: 3,
  room: "tower",
  sender: "Mayday",
  tag: "FLIGHT PLAN",
  face: null,
  text: "FLIGHT PLAN\ntask: refunds\nedit: billing/refunds.py\nuses: auth.session.create_session",
};

export const TRAFFIC: FeedMessage = {
  id: 4,
  room: "tower",
  sender: "Detente",
  tag: "TRAFFIC",
  face: "[¬_¬]",
  text: "Mayday · cleared billing/refunds.py\nMayday uses create_session, which Wilco is changing. Watching.",
};

export const COLLISION: FeedMessage = {
  id: 5,
  room: "tower",
  sender: "Detente",
  tag: "COLLISION",
  face: "[O_O]!",
  text: "Wilco changed create_session(user) to create_session(user, ttl)\nMayday's billing/refunds.py:5 is missing required argument ttl\nNothing pushed. Both flights holding.\nOpened conflict-create-session-3f1a.",
};

export const DECISION: FeedMessage = {
  id: 6,
  room: "conflict-create-session-3f1a",
  sender: "Detente",
  tag: "DECISION",
  face: "[O_O]!",
  text: "lay or developer-a, reply A or B\nA  Give ttl a default  (Wilco edits)\nB  Update the call at billing/refunds.py:5  (Mayday edits)",
};

export const REPLY: FeedMessage = {
  id: 7,
  room: "conflict-create-session-3f1a",
  sender: "you",
  tag: null,
  face: null,
  text: "A",
};

export const DECIDED: FeedMessage = {
  id: 8,
  room: "conflict-create-session-3f1a",
  sender: "Detente",
  tag: "DECIDED",
  face: "[^_^]",
  text: "by you (A): Give ttl a default. Wilco makes the edit.",
};

export const RESOLVED: FeedMessage = {
  id: 9,
  room: "tower",
  sender: "Detente",
  tag: "RESOLVED",
  face: "[^_^]",
  text: "conflict-create-session-3f1a: the code fits again. 0 open collisions.",
};
