"use client";

import { RadarScreen } from "@/components/radar-screen";
import { usePlayback } from "./playback";
import { StoryPanel } from "./story-panel";

export function ShowcaseRadar() {
  const { state } = usePlayback();

  return (
    <div className="shaken contents" data-mood={state.mood}>
      <RadarScreen
        title="Showcase radar"
        state={state}
        conflictHref={() => "/showcase/conflicts"}
        guide={<StoryPanel />}
      />
    </div>
  );
}
