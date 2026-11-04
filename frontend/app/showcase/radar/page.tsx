import type { Metadata } from "next";
import { ShowcaseRadar } from "../_story/showcase-radar";

export const metadata: Metadata = { title: "Radar" };

export default function ShowcaseRadarPage() {
  return <ShowcaseRadar />;
}
