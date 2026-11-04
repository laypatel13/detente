"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useEffect } from "react";
import { Roger } from "@/components/sprite";
import { Button } from "@/components/ui/button";
import { MOOD_SIGN } from "@/lib/radar";
import { usePlayback } from "./playback";
import type { Choice } from "./story";

const WORD_DELAY = 0.03;

// Words come in one by one, but they're all on the page from the start, so nothing jumps.
function RogerSays({ text }: { text: string }) {
  return (
    <p className="text-[17px] leading-snug">
      {text.split(" ").map((word, index) => (
        <motion.span
          key={`${text}-${index}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: index * WORD_DELAY, duration: 0.05 }}
        >
          {word}{" "}
        </motion.span>
      ))}
    </p>
  );
}

function PickButtons() {
  const { state, decide } = usePlayback();

  return (
    <div className="grid gap-2">
      {state.conflicts[0].options.map((option) => (
        <button
          key={option.key}
          type="button"
          onClick={() => decide(option.key as Choice)}
          className="flex w-full cursor-pointer items-center gap-3 bg-paint p-2 text-left text-tarmac transition-colors hover:bg-runway active:translate-y-0.5"
        >
          <span className="display flex size-12 shrink-0 items-center justify-center border-2 border-runway bg-tarmac text-3xl text-runway">
            {option.key}
          </span>
          <span className="min-w-0">
            <span className="block leading-tight font-medium">{option.text}</span>
            <span className="block text-sm">{option.agent} edits</span>
          </span>
        </button>
      ))}
    </div>
  );
}

function Actions() {
  const { stop, watching, canPick, advance, restart } = usePlayback();

  if (watching) return null;
  if (canPick) return <PickButtons />;
  if (stop.action.kind === "next") {
    return (
      <Button
        size="lg"
        variant={MOOD_SIGN[stop.mood] === "traffic" ? "ink" : "default"}
        onClick={advance}
        className="w-full"
      >
        {stop.action.label}
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      <Button asChild size="lg">
        <Link href="/get-started">Set it up on your project</Link>
      </Button>
      <Button size="lg" variant="outline" onClick={restart}>
        Pick the other fix
      </Button>
    </div>
  );
}

export function StoryPanel() {
  const { state, stop, choice, watching, canPick, progress, decide } = usePlayback();
  const mood = watching ? state.mood : stop.mood;
  const text = typeof stop.text === "string" ? stop.text : stop.text[choice ?? "A"];

  useEffect(() => {
    if (!canPick) return;
    const pick = (event: KeyboardEvent) => {
      const key = event.key.toUpperCase();
      if ((key === "A" || key === "B") && !event.metaKey && !event.ctrlKey) decide(key);
    };
    window.addEventListener("keydown", pick);
    return () => window.removeEventListener("keydown", pick);
  }, [canPick, decide]);

  return (
    <section
      aria-live="polite"
      aria-label="Roger"
      className="field flex flex-col gap-3 border-4 border-transparent p-4 transition-colors duration-200 sm:p-5"
      data-kind={MOOD_SIGN[mood]}
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0 max-sm:[&_canvas]:!h-24 max-sm:[&_canvas]:!w-[4.5rem]">
          <Roger mood={mood} scale={5} />
        </div>
        <div className="grid min-w-0 flex-1 gap-2">
          <div className="flex items-start justify-between gap-3">
            <h2 className="display text-[2.5rem]">{stop.title}</h2>
            <ol
              aria-label={`Part ${progress.at + 1} of ${progress.of}`}
              className="mt-2 flex shrink-0 gap-1"
            >
              {Array.from({ length: progress.of }, (_, index) => (
                <li
                  key={index}
                  className="size-2.5 bg-current"
                  style={{ opacity: index <= progress.at ? 1 : 0.3 }}
                />
              ))}
            </ol>
          </div>
          <RogerSays text={watching ? `${watching} ${state.headline}` : text} />
        </div>
      </div>
      <Actions />
      {canPick && (
        <Link href="/showcase/conflicts" className="font-medium underline underline-offset-4">
          {stop.action.kind === "pick" && stop.action.label}
        </Link>
      )}
      {!watching && (
        <p className="text-[15px] leading-snug">
          <strong className="font-semibold">For real:</strong> {stop.forReal}
        </p>
      )}
    </section>
  );
}
