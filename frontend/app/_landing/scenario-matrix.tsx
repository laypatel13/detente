"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export type Result = "quiet" | "flagged" | "stop" | "heads-up";
export type Scenario = { name: string; breaks: boolean; results: Result[] };

const TOOLS = ["git merge-tree", "File leases", "Detente"];

// A check that flags a scenario stops it, whichever tool it is, so both read as red.
const LIGHT: Record<Result, string> = {
  stop: "bg-hold",
  flagged: "bg-hold",
  "heads-up": "bg-runway",
  quiet: "bg-raised",
};

const SAYS: Record<Result, string> = {
  stop: "stops it",
  flagged: "stops it",
  "heads-up": "warns",
  quiet: "says nothing",
};

function describe(scenario: Scenario) {
  const results = TOOLS.map((tool, index) => `${tool} ${SAYS[scenario.results[index]]}`);
  return `${scenario.name}. ${scenario.breaks ? "Really breaks" : "Fine"}: ${results.join(", ")}.`;
}

// Every scenario is one column of three lights, one per check, like a row of runway lights.
export function ScenarioMatrix({ scenarios }: { scenarios: Scenario[] }) {
  const [active, setActive] = useState(scenarios[0]);
  const groups = [
    { title: `${scenarios.filter((s) => s.breaks).length} that really break`, rows: scenarios.filter((s) => s.breaks) },
    { title: `${scenarios.filter((s) => !s.breaks).length} that are fine`, rows: scenarios.filter((s) => !s.breaks) },
  ];

  return (
    <div className="grid gap-6">
      <div className="grid gap-x-8 gap-y-8 lg:grid-cols-[minmax(0,20fr)_minmax(0,12fr)]">
        {groups.map((group) => (
          <div key={group.title} className="grid content-start gap-3">
            <h4 className="font-display text-2xl font-bold uppercase">{group.title}</h4>
            <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 sm:grid-cols-[8rem_minmax(0,1fr)]">
              <ul aria-hidden className="grid gap-1 py-0.5 text-sm sm:text-base">
                {TOOLS.map((tool) => (
                  <li key={tool} className="flex h-5 items-center whitespace-nowrap sm:h-7">
                    {tool}
                  </li>
                ))}
              </ul>
              <ul className="flex gap-0.5 sm:gap-1">
                {group.rows.map((scenario) => (
                  <li key={scenario.name} className="min-w-0 flex-1">
                    <button
                      type="button"
                      aria-label={describe(scenario)}
                      aria-pressed={active === scenario}
                      onMouseEnter={() => setActive(scenario)}
                      onFocus={() => setActive(scenario)}
                      onClick={() => setActive(scenario)}
                      className={cn(
                        "grid w-full cursor-pointer gap-1 p-0.5 outline-offset-2 transition-colors hover:bg-paint/20",
                        active === scenario && "bg-paint",
                      )}
                    >
                      {scenario.results.map((result, index) => (
                        <span key={TOOLS[index]} className={cn("block h-4 sm:h-6", LIGHT[result])} />
                      ))}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      <p aria-live="polite" className="min-h-[3.5em] max-w-[80ch] text-lg leading-relaxed">
        <span className="font-semibold">{active.name}.</span>{" "}
        {active.breaks ? "Really breaks" : "Fine"}:{" "}
        {TOOLS.map((tool, index) => `${tool} ${SAYS[active.results[index]]}`).join(", ")}.
      </p>

      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-base">
        <li className="flex items-center gap-2">
          <span aria-hidden className="size-4 bg-hold" /> Stopped
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden className="size-4 bg-runway" /> Warned
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden className="size-4 bg-raised" /> Said nothing
        </li>
      </ul>
    </div>
  );
}
