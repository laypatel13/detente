"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiDown } from "@/components/api-down";
import { ConflictScreen } from "@/components/conflict-screen";
import type { Conflict } from "@/lib/radar";
import { useRadar } from "@/lib/use-radar";

export function LiveConflict({ id }: { id: string }) {
  const { state, connection } = useRadar();
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [missing, setMissing] = useState(false);
  const version = state?.version;

  useEffect(() => {
    let current = true;
    fetch(`/api/radar/conflicts/${encodeURIComponent(id)}`)
      .then(async (response) => {
        if (!current) return;
        if (response.status === 404) setMissing(true);
        else if (response.ok) setConflict(await response.json());
      })
      .catch(() => {});
    return () => {
      current = false;
    };
  }, [id, version]);

  if (missing) {
    return (
      <p>
        No conflict named <code className="font-mono">{id}</code>.{" "}
        <Link href="/radar" className="underline underline-offset-4">
          Back to the radar
        </Link>
      </p>
    );
  }
  if (!conflict) return connection === "lost" ? <ApiDown /> : <p className="text-dim">Loading</p>;

  return (
    <ConflictScreen conflict={conflict}>
      <p className="text-dim">
        {conflict.status === "open"
          ? "Waiting for a person to reply A or B in the conflict room."
          : "Decided in the conflict room."}{" "}
        Every decision happens in Switch chat, so this page has nothing to click.
      </p>
    </ConflictScreen>
  );
}
