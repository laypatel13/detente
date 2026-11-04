"use client";

import { type ReactNode, useState } from "react";
import { Sign } from "@/components/sign";
import type { SignKind } from "@/lib/radar";
import { cn } from "@/lib/utils";

type Check = {
  name: string;
  verdict: string;
  sign: SignKind;
  says: string;
  output: ReactNode;
};

const CHECKS: Check[] = [
  {
    name: "File lock",
    verdict: "Quiet",
    sign: "plain",
    says: "Each agent holds a different file, so no lock is ever contested.",
    output: (
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-dim">
            <th className="px-2 py-2 font-medium">Locked file</th>
            <th className="px-2 py-2 font-medium">Held by</th>
          </tr>
        </thead>
        <tbody>
          <tr className="bg-panel">
            <td className="px-2 py-2">
              <code className="font-mono">auth/session.py</code>
            </td>
            <td className="px-2 py-2">
              <code className="font-mono">Wilco</code>
            </td>
          </tr>
          <tr>
            <td className="px-2 py-2">
              <code className="font-mono">billing/refunds.py</code>
            </td>
            <td className="px-2 py-2">
              <code className="font-mono">Mayday</code>
            </td>
          </tr>
        </tbody>
      </table>
    ),
  },
  {
    name: "git merge",
    verdict: "Quiet",
    sign: "plain",
    says: "No lines overlap, so git calls it a clean merge.",
    output: (
      <pre className="overflow-x-auto font-mono text-sm leading-7">
        {"$ git merge-tree --write-tree wilco mayday\n"}
        {"584d5870bac08d083319f44686e848a533ac1f0f\n"}
        {"$ echo $?\n0"}
      </pre>
    ),
  },
  {
    name: "The build",
    verdict: "Broken",
    sign: "hold",
    says: "Both branches pushed and merged, and now it crashes. This is when most teams find out.",
    output: (
      <pre className="overflow-x-auto font-mono text-sm leading-7">
        {'  File "billing/refunds.py", line 5, in refund\n'}
        {"    session = create_session(user)\n"}
        <span className="text-beacon">
          {"TypeError: create_session() missing 1\nrequired positional argument: 'ttl'"}
        </span>
      </pre>
    ),
  },
  {
    name: "Detente",
    verdict: "Caught",
    sign: "traffic",
    says: "Caught across laptops, before anyone pushed. Both flights hold until a person picks the fix.",
    output: (
      <div className="grid gap-2 text-sm">
        <p className="flex flex-wrap items-center gap-2">
          <span className="font-medium">Detente</span>
          <span className="text-dim">in tower</span>
          <Sign kind="hold" className="!border-1 text-sm">
            Collision
          </Sign>
        </p>
        <pre className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap">
          {
            "[O_O]! Wilco changed create_session(user) to create_session(user, ttl)\nMayday's billing/refunds.py:5 is missing required argument ttl\nNothing pushed. Both flights holding.\nOpened conflict-create-session-3f1a."
          }
        </pre>
      </div>
    ),
  },
];

export function SameEdits() {
  const [picked, setPicked] = useState(0);
  const check = CHECKS[picked];

  return (
    <div className="mt-12 grid gap-8 lg:grid-cols-[5fr_7fr] lg:gap-12">
      <div className="rise grid content-start gap-1">
        {CHECKS.map((item, index) => (
          <button
            key={item.name}
            type="button"
            aria-pressed={index === picked}
            onClick={() => setPicked(index)}
            className={cn(
              "group flex cursor-pointer items-center justify-between gap-4 py-2 text-left transition-colors",
              index === picked ? "text-runway" : "text-dim hover:text-ink",
            )}
          >
            <span className="display text-[clamp(2.75rem,5vw,4.75rem)]">{item.name}</span>
            <Sign kind={item.sign} className="text-lg">
              {item.verdict}
            </Sign>
          </button>
        ))}
      </div>

      <div className="rise-2 grid min-w-0 content-start gap-3 bg-panel p-4 sm:p-8" data-ui>
        <div className="grid gap-3 sm:grid-cols-2">
          <figure className="m-0 min-w-0 bg-sky p-3">
            <figcaption className="text-sm text-dim">Wilco, auth/session.py</figcaption>
            <pre className="mt-2 overflow-x-auto font-mono text-[13px] leading-6">
              <span className="text-beacon">- def create_session(user):</span>
              {"\n"}
              <span className="text-runway">+ def create_session(user, ttl):</span>
            </pre>
          </figure>
          <figure className="m-0 min-w-0 bg-sky p-3">
            <figcaption className="text-sm text-dim">Mayday, billing/refunds.py:5</figcaption>
            <pre className="mt-2 overflow-x-auto font-mono text-[13px] leading-6">
              {"  session = create_session(user)\n  # nothing changed here"}
            </pre>
          </figure>
        </div>

        <div key={check.name} className="min-h-56 bg-tarmac p-4 animate-in fade-in duration-200">
          <p className="mb-4 text-base font-medium">{check.says}</p>
          {check.output}
        </div>
      </div>
    </div>
  );
}
