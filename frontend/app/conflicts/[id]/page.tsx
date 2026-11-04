import type { Metadata } from "next";
import { Suspense } from "react";
import { AppHeader } from "@/components/app-header";
import { LiveConflict } from "@/components/live-conflict";

export const metadata: Metadata = { title: "Conflict" };

type Params = Promise<{ id: string }>;

async function Conflict({ params }: { params: Params }) {
  const { id } = await params;
  return <LiveConflict id={id} />;
}

export default function ConflictPage({ params }: { params: Params }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6">
        <Suspense fallback={<p className="text-dim">Loading</p>}>
          <Conflict params={params} />
        </Suspense>
      </main>
    </div>
  );
}
