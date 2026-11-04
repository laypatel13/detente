"use client";

import { ApiDown } from "@/components/api-down";
import { AppHeader } from "@/components/app-header";
import { RadarScreen } from "@/components/radar-screen";
import { useRadar } from "@/lib/use-radar";

export function LiveRadar() {
  const { state, connection } = useRadar();

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader />
      <RadarScreen
        title="Live radar"
        state={state}
        conflictHref={(id) => `/conflicts/${id}`}
        guide={connection === "lost" ? <ApiDown /> : undefined}
      />
    </div>
  );
}
