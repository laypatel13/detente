"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ConflictScreen } from "@/components/conflict-screen";
import { Roger } from "@/components/sprite";
import { Button } from "@/components/ui/button";
import { usePlayback } from "./playback";
import type { Choice } from "./story";

export function ShowcaseConflict() {
  const { state, canPick, decide } = usePlayback();
  const router = useRouter();
  const conflict = state.conflicts[0];

  if (!conflict) {
    return (
      <div className="grid min-h-[calc(100svh-7rem)] content-center items-center gap-10 lg:grid-cols-[auto_minmax(0,1fr)] lg:gap-16">
        <Roger mood="resting" scale={9} />
        <div className="grid max-w-[60ch] justify-items-start gap-5">
          <h1 className="font-display text-[clamp(1.75rem,4.4vw,3.75rem)] leading-[1.02] font-bold text-balance">
            Nothing to decide yet
          </h1>
          <p className="text-lg leading-relaxed lg:text-xl">
            The flights are still clear. When two of them collide, the conflict opens here: what
            changed, whose unpushed code it breaks, and the two fixes a person picks from.
          </p>
          <Button asChild size="lg">
            <Link href="/showcase/radar">Back to the radar</Link>
          </Button>
        </div>
      </div>
    );
  }

  function pick(key: string) {
    decide(key as Choice);
    router.push("/showcase/radar");
  }

  return (
    <ConflictScreen conflict={conflict} onPick={canPick ? pick : undefined}>
      <p className="text-dim">
        {canPick
          ? "Pick a fix. In the real app you'd reply A or B in your team's chat, and this page has nothing to click."
          : "In the real app this page has nothing to click, because every decision happens in chat."}
      </p>
    </ConflictScreen>
  );
}
