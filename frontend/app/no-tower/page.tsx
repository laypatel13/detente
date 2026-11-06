import type { Metadata } from "next";
import Link from "next/link";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { Roger } from "@/components/sprite";
import { TowerAction } from "@/components/tower";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Your radar" };

// Shown in place of the sign-in and the radar on a copy of the site with no tower behind it.
export default function NoTowerPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader links={PUBLIC_LINKS}>
        <TowerAction />
      </SiteHeader>
      <main className="grid flex-1 content-center items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8">
        <div className="grid justify-items-start gap-6 lg:col-span-8">
          <h1 className="display text-[clamp(2.75rem,8vw,8.5rem)]">
            The radar runs on your machine
          </h1>
          <p className="max-w-[54ch] text-xl leading-relaxed">
            This copy of the website has no Detente behind it, so there&apos;s nothing to sign in
            to. Each team runs its own tower, and its radar opens on that machine at
            localhost:3100.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="lg">
              <Link href="/get-started">Run it yourself</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/showcase">Play the showcase</Link>
            </Button>
          </div>
        </div>
        <figure className="location m-0 grid justify-items-center gap-4 p-10 lg:col-span-4">
          <Roger mood="resting" scale={9} />
          <figcaption className="text-lg">
            No tower here, so Roger&apos;s off duty.
          </figcaption>
        </figure>
      </main>
    </div>
  );
}
