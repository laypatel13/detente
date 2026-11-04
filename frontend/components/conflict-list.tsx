"use client";

import Link from "next/link";
import { ApiDown } from "@/components/api-down";
import { Sign } from "@/components/sign";
import { conflictHeadline } from "@/lib/radar";
import { useRadar } from "@/lib/use-radar";

export function ConflictList() {
  const { state, connection } = useRadar();

  if (!state) return connection === "lost" ? <ApiDown /> : <p className="text-dim">Loading</p>;
  if (!state.conflicts.length) {
    return <p className="text-dim">No open conflicts. Your flights are clear.</p>;
  }

  return (
    <ul className="grid gap-2">
      {state.conflicts.map((conflict) => (
        <li key={conflict.id}>
          <Link
            href={`/conflicts/${conflict.id}`}
            className="flex items-center gap-4 bg-panel p-4 transition-colors hover:bg-raised"
          >
            <Sign kind={conflict.status === "open" ? "hold" : "traffic"} className="text-lg">
              {conflict.status === "open" ? "Hold" : "Fix under way"}
            </Sign>
            <span className="min-w-0">
              <span className="block font-medium">{conflictHeadline(conflict)}</span>
              <code className="block truncate font-mono text-sm text-dim">{conflict.id}</code>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
