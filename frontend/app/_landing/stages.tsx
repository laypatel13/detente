"use client";

import { useState } from "react";
import { FlightStrip } from "@/components/flight-strip";
import { Roger } from "@/components/sprite";
import { SwitchFeed } from "@/components/switch-feed";
import type { FeedMessage, Flight, FlightStatus, Mood, SignKind } from "@/lib/radar";
import { cn } from "@/lib/utils";
import { CLEARED, COLLISION, DECIDED, DECISION, FLIGHT_PLAN, REPLY, TRAFFIC, USES } from "./messages";

function layClaude(status: FlightStatus): Flight {
  return {
    callsign: "Wilco",
    owner: "lay",
    task: "session expiry",
    files: ["auth/session.py"],
    sector: "auth",
    status,
  };
}

function aCodex(status: FlightStatus): Flight {
  return {
    callsign: "Mayday",
    owner: "a",
    task: "refunds",
    files: ["billing/refunds.py"],
    sector: "billing",
    status,
  };
}

type Stage = {
  name: string;
  clause: string;
  text: string;
  mood: Mood;
  sign: SignKind;
  feed: FeedMessage[];
  flights: Flight[];
};

const STAGES: Stage[] = [
  {
    name: "Flight plan",
    clause: "First, a flight plan",
    text: "Before it touches code, an agent says in team chat what it will edit and what it will change. A hook refuses edits without a plan.",
    mood: "watching",
    sign: "cleared",
    feed: [FLIGHT_PLAN, CLEARED],
    flights: [layClaude("cleared")],
  },
  {
    name: "Traffic",
    clause: "Then, a heads-up",
    text: "When one plan uses something another plan changes, both teammates hear about it before any code exists.",
    mood: "traffic",
    sign: "traffic",
    feed: [USES, TRAFFIC],
    flights: [layClaude("cleared"), aCodex("cleared")],
  },
  {
    name: "Collision",
    clause: "A real break holds both",
    text: "Detente reads the code on every laptop. If one agent's change breaks another's unpushed work, both flights hold and a conflict room opens.",
    mood: "collision",
    sign: "hold",
    feed: [COLLISION],
    flights: [layClaude("worried"), aCodex("worried")],
  },
  {
    name: "Decision",
    clause: "A person picks the fix",
    text: "You reply A or B in chat. The right agent makes the edit, Detente checks the code fits again, and the flights carry on.",
    mood: "resolved",
    sign: "traffic",
    feed: [DECISION, REPLY, DECIDED],
    flights: [layClaude("cleared"), aCodex("cleared")],
  },
];

const LAST = STAGES.length - 1;

export function Stages() {
  const [at, setAt] = useState(0);
  const stage = STAGES[at];

  return (
    <section aria-labelledby="stage-title">
      <div className="grid lg:min-h-[78svh] lg:grid-cols-2">
        <div
          className="field flex flex-col justify-between gap-8 p-6 transition-colors duration-200 sm:p-10 lg:p-12"
          data-kind={stage.sign}
        >
          <div key={stage.name} className="grid gap-5 animate-in fade-in duration-200">
            <h2 id="stage-title" className="display text-[clamp(2.75rem,5.4vw,5.5rem)] text-balance">
              {stage.clause}
            </h2>
            <p className="max-w-[46ch] text-lg leading-relaxed">{stage.text}</p>
          </div>
          <div className="self-end max-sm:[&_canvas]:!h-48 max-sm:[&_canvas]:!w-36">
            <Roger mood={stage.mood} scale={11} />
          </div>
        </div>

        <div className="flex min-h-[28rem] items-center justify-center bg-panel p-4 sm:p-10">
          <div
            key={stage.name}
            data-ui
            className="grid w-full max-w-[36rem] gap-4 animate-in fade-in duration-200"
          >
            <ul className="space-y-1">
              {stage.flights.map((flight) => (
                <FlightStrip key={flight.callsign} flight={flight} />
              ))}
            </ul>
            <div className="bg-sky p-4">
              <SwitchFeed feed={stage.feed} />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-tarmac px-4 pt-8 pb-6 sm:px-6 lg:px-8">
        <div className="relative">
          <div aria-hidden className="absolute inset-x-0 top-3 h-2 bg-raised" />
          <div
            aria-hidden
            className="absolute top-3 left-0 h-2 bg-paint transition-[width] duration-200"
            style={{ width: `${(at / LAST) * 100}%` }}
          />
          <input
            type="range"
            min={0}
            max={LAST}
            step={1}
            value={at}
            onChange={(event) => setAt(Number(event.target.value))}
            aria-label="Stage"
            aria-valuetext={stage.name}
            className="stage-range"
          />
        </div>
        <div className="mt-2 flex justify-between gap-2">
          {STAGES.map((item, index) => (
            <button
              key={item.name}
              type="button"
              onClick={() => setAt(index)}
              className={cn(
                "min-h-11 cursor-pointer text-lg font-medium transition-colors",
                index === at ? "text-runway" : "text-dim hover:text-ink",
              )}
            >
              {item.name}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
