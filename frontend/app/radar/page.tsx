import type { Metadata } from "next";
import { LiveRadar } from "@/components/live-radar";

export const metadata: Metadata = { title: "Radar" };

export default function RadarPage() {
  return <LiveRadar />;
}
