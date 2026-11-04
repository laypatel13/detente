import type { Metadata } from "next";
import Link from "next/link";
import { Sign } from "@/components/sign";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { PlaybackProvider } from "./_story/playback";

export const metadata: Metadata = { title: { default: "Showcase", template: "%s | Showcase" } };

const SHOWCASE_LINKS = [
  { href: "/showcase/radar", label: "Radar" },
  { href: "/showcase/conflicts", label: "Conflicts" },
];

export default function ShowcaseLayout({ children }: LayoutProps<"/showcase">) {
  const note = (
    <p className="flex items-center gap-2 text-[15px]">
      <Sign kind="traffic" className="text-[15px]">
        Recording
      </Sign>
      A real run, played back. Nothing here is live.
    </p>
  );

  return (
    <PlaybackProvider>
      <div className="flex min-h-dvh flex-col">
        <SiteHeader links={SHOWCASE_LINKS} note={note}>
          <Button asChild variant="outline" className="hidden sm:inline-flex">
            <Link href="/get-started">Use it on your project</Link>
          </Button>
        </SiteHeader>
        {children}
      </div>
    </PlaybackProvider>
  );
}
