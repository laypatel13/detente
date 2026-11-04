"use client";

import { useEffect, useMemo, useRef } from "react";
import plane from "@/lib/art/plane.json";
import roger from "@/lib/art/roger.json";
import type { CrewStatus, FlightStatus, Mood, Owner } from "@/lib/radar";

type Frames = string[][];
type Palette = Record<string, string>;
type Art = {
  width: number;
  height: number;
  palette?: Palette;
  shared?: Palette;
  accent?: Record<string, Palette>;
  owners?: Record<string, Palette>;
  moods: Record<string, { frames: Frames; says: string }>;
};

const ROGER = roger as Art;
const PLANE = plane as Art;
const HEAD_ROWS = 14;

export const ROGER_SIZE = { width: ROGER.width, height: ROGER.height };
export const PLANE_SIZE = { width: PLANE.width, height: PLANE.height };

const ROGER_SPEED: Partial<Record<Mood, number>> = { collision: 500 };
const PLANE_MOOD: Record<FlightStatus, string> = {
  cleared: "cleared",
  hold: "hold",
  worried: "worried",
  landed: "happy",
};

type SpriteProps = {
  frames: Frames;
  palette: Palette;
  scale: number;
  label: string;
  speed?: number;
};

// Sprites stay on whole-number scales so every pixel keeps a square edge.
export function Sprite({ frames, palette, scale, label, speed = 900 }: SpriteProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const width = frames[0][0].length;
  const height = frames[0].length;

  useEffect(() => {
    const context = ref.current?.getContext("2d");
    if (!context) return;

    const paint = (rows: string[]) => {
      context.clearRect(0, 0, width, height);
      rows.forEach((row, y) => {
        for (let x = 0; x < row.length; x++) {
          if (row[x] === ".") continue;
          context.fillStyle = palette[row[x]];
          context.fillRect(x, y, 1, 1);
        }
      });
    };

    let frame = 0;
    paint(frames[0]);
    if (frames.length < 2 || matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const timer = setInterval(() => {
      frame = (frame + 1) % frames.length;
      paint(frames[frame]);
    }, speed);
    return () => clearInterval(timer);
  }, [frames, palette, speed, width, height]);

  return (
    <canvas
      ref={ref}
      width={width}
      height={height}
      role="img"
      aria-label={label}
      className="block"
      style={{ width: width * scale, height: height * scale, imageRendering: "pixelated" }}
    />
  );
}

export function Roger({
  mood,
  scale,
  head = false,
}: {
  mood: Mood;
  scale: number;
  head?: boolean;
}) {
  const palette = useMemo(() => ({ ...ROGER.palette, ...ROGER.accent?.[mood] }), [mood]);
  const frames = useMemo(() => {
    const all = ROGER.moods[mood].frames;
    return head ? all.map((rows) => rows.slice(0, HEAD_ROWS)) : all;
  }, [mood, head]);

  return (
    <Sprite
      frames={frames}
      palette={palette}
      scale={scale}
      label={`Roger, ${ROGER.moods[mood].says}`}
      speed={ROGER_SPEED[mood]}
    />
  );
}

// Roger's head on a yellow sign with a black edge, like the app icon, so it reads on any ground.
export function RogerBadge({ mood, scale }: { mood: Mood; scale: number }) {
  return (
    <span
      className="inline-flex shrink-0 rounded-[var(--radius)] border-2 border-tarmac bg-runway"
      style={{ padding: scale * 2 }}
    >
      <Roger mood={mood} scale={scale} head />
    </span>
  );
}

export function Plane({
  owner,
  status,
  scale,
  label,
}: {
  owner: Owner;
  status: Exclude<CrewStatus, "parked">;
  scale: number;
  label: string;
}) {
  const palette = useMemo(() => ({ ...PLANE.shared, ...PLANE.owners?.[owner] }), [owner]);
  return (
    <Sprite
      frames={PLANE.moods[PLANE_MOOD[status]].frames}
      palette={palette}
      scale={scale}
      label={label}
      speed={110}
    />
  );
}
