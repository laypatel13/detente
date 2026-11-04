"use client";

import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { type Choice, PICK_STOP, STOPS, timeline } from "./story";

const SLOWEST_FRAME_MS = 1100;
const FASTEST_FRAME_MS = 400;

function usePlaybackState() {
  const [stopIndex, setStopIndex] = useState(0);
  const [frameIndex, setFrameIndex] = useState(0);
  const [choice, setChoice] = useState<Choice | null>(null);

  const frames = timeline(choice);
  const frame = frames[frameIndex];
  const arrived = STOPS[stopIndex].reached(frame.state);
  const nextAt = frames[frameIndex + 1]?.at;

  useEffect(() => {
    if (arrived) return;
    const gap = (nextAt - frame.at) * 1000;
    const wait = Math.min(SLOWEST_FRAME_MS, Math.max(FASTEST_FRAME_MS, gap));
    const timer = setTimeout(() => setFrameIndex((index) => index + 1), wait);
    return () => clearTimeout(timer);
  }, [arrived, frame.at, nextAt]);

  return {
    state: frame.state,
    choice,
    progress: { at: arrived ? stopIndex : stopIndex - 1, of: STOPS.length },
    stop: STOPS[arrived ? stopIndex : stopIndex - 1],
    watching: arrived ? null : STOPS[stopIndex].watching,
    canPick: arrived && stopIndex === PICK_STOP,
    advance: () => setStopIndex((index) => index + 1),
    decide: (key: Choice) => {
      setChoice(key);
      setStopIndex(PICK_STOP + 1);
    },
    restart: () => {
      setStopIndex(0);
      setFrameIndex(0);
      setChoice(null);
    },
  };
}

type Playback = ReturnType<typeof usePlaybackState>;

const PlaybackContext = createContext<Playback | null>(null);

// In the layout, so the story keeps its place between the radar and the conflict page.
export function PlaybackProvider({ children }: { children: ReactNode }) {
  return <PlaybackContext.Provider value={usePlaybackState()}>{children}</PlaybackContext.Provider>;
}

export function usePlayback() {
  const playback = useContext(PlaybackContext);
  if (!playback) throw new Error("usePlayback needs a PlaybackProvider");
  return playback;
}
