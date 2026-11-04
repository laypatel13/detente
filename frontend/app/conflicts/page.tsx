import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import { ConflictList } from "@/components/conflict-list";

export const metadata: Metadata = { title: "Conflicts" };

export default function ConflictsPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader />
      <main className="mx-auto grid w-full max-w-3xl flex-1 content-start gap-6 px-4 py-10 sm:px-6">
        <h1 className="display text-6xl">Conflicts</h1>
        <ConflictList />
      </main>
    </div>
  );
}
