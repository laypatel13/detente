import type { Metadata } from "next";
import Link from "next/link";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { Roger } from "@/components/sprite";

export const metadata: Metadata = { title: "Set up" };

const STEPS = [
  {
    title: "Start Detente on one machine",
    text: "This runs Switch, your team's chat, Detente and the radar. You need Docker, uv and Node 24.",
    code: "make install\nmake switch-up\nmake setup\nmake up",
  },
  {
    title: "Make your sign-in",
    text: "It asks for a password of at least 12 characters. Run it once for each teammate.",
    code: "make user NAME=yourname",
  },
  {
    title: "Open your radar",
    text: "Sign in here. Only your team's accounts can see it.",
    code: "http://localhost:3100/radar",
  },
  {
    title: "Connect each laptop",
    text: "Install the detente command, then connect each checkout an agent works in. It asks for the pilot token, which is DETENTE_PILOT_TOKEN in your .env file. Leave watch running, and run doctor if anything seems off.",
    code: 'uv tool install detente\n\ncd /path/to/your/repo\ndetente connect --callsign lay-claude --person lay \\\n  --vendor "Claude Code" --url http://localhost:8100\n\ndetente watch',
  },
];

export default function GetStartedPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader links={PUBLIC_LINKS} />
      <main className="grid flex-1 content-start gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[5fr_7fr] lg:gap-12 lg:px-8">
        <header className="grid content-start justify-items-start gap-4 self-start lg:sticky lg:top-10">
          <Roger mood="watching" scale={6} />
          <h1 className="display text-[clamp(2.75rem,5.4vw,5.5rem)]">
            Set up Detente on your project
          </h1>
          <p className="text-lg leading-relaxed">
            Detente runs on your team&apos;s own machines, so your radar lives there too, not on
            this website. Want to see it first?{" "}
            <Link href="/showcase" className="underline underline-offset-4">
              Try the showcase
            </Link>
            .
          </p>
        </header>

        <ol className="grid min-w-0 gap-10">
          {STEPS.map((step) => (
            <li key={step.title} className="grid gap-2">
              <h2 className="display text-3xl">{step.title}</h2>
              <p className="text-dim">{step.text}</p>
              <pre className="overflow-x-auto bg-tarmac p-4 font-mono text-sm leading-7">
                {step.code}
              </pre>
            </li>
          ))}
        </ol>
      </main>
    </div>
  );
}
