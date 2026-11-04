import type { Metadata } from "next";
import { ShowcaseConflict } from "../_story/showcase-conflict";

export const metadata: Metadata = { title: "Conflicts" };

export default function ShowcaseConflictsPage() {
  return (
    <main className="mx-auto w-full max-w-[1640px] flex-1 px-4 pt-2 pb-10 sm:px-6 lg:px-8">
      <ShowcaseConflict />
    </main>
  );
}
