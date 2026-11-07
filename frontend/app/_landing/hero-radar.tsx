"use client";

import { useEffect, useState } from "react";
import { RadarScope } from "@/components/radar-scope";
import { RadioLine } from "@/components/radio-line";
import type { RadarState } from "@/lib/radar";

const SHOWN_FOR_MS = [3000, 3500, 7000];

// Opens on the collision, so a still page and reduced motion both show the whole point.
export function HeroRadar({ frames }: { frames: RadarState[] }) {
  const [index, setIndex] = useState(frames.length - 1);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = setTimeout(
      () => setIndex((index + 1) % frames.length),
      SHOWN_FOR_MS[index],
    );
    return () => clearTimeout(timer);
  }, [index, frames.length, paused]);

  return (
    <>
      <RadarScope state={frames[index]} paused={paused} onPausedChange={setPaused} />
      <div aria-hidden data-ui className="min-h-14">
        <RadioLine state={frames[index]} decode />
      </div>
    </>
  );
}
