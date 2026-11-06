import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { SignArrow } from "@/components/sign-arrow";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { Plane, RogerBadge } from "@/components/sprite";
import { IfTower, REPO_URL, TowerAction } from "@/components/tower";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Run it yourself" };

type Step = { title: string; text: ReactNode; code?: string; action?: ReactNode };

const RADAR = "http://localhost:3100/radar";

// Everything here happens once, on the one machine the whole team shares.
const TOWER_STEPS: Step[] = [
  {
    title: "Get the code",
    text: "You need Docker, uv and Node 24 on this machine.",
    code: `git clone ${REPO_URL}\ncd detente`,
  },
  {
    title: "Start it",
    text: "This starts Switch, your team's chat, then Detente and the radar, all in Docker.",
    code: "make install\nmake switch-up\nmake setup\nmake up",
  },
  {
    title: "Let the team's laptops in",
    text: (
      <>
        Skip this if every agent works on this machine. Otherwise, add this machine&apos;s IP
        address on your team&apos;s private network, such as its{" "}
        <a href="https://tailscale.com" className="underline underline-offset-2">
          Tailscale
        </a>{" "}
        address, and restart. Teammates then use it wherever this page says localhost.
      </>
    ),
    code: 'echo "TOWER_ADDR=100.101.102.103" >> .env\nmake switch-up up',
  },
  {
    title: "Make a sign-in for each teammate",
    text: "Run it here on the tower machine. It asks for a password of at least 12 characters. There's no sign-up page anywhere.",
    code: "make user NAME=yourname",
  },
  {
    title: "Open your radar",
    text: "Sign in with the account you just made. Only your team's accounts can see it.",
    action: (
      <IfTower otherwise={<Code>{RADAR}</Code>}>
        <Button asChild size="lg" className="justify-self-start">
          <Link href="/radar">Open your radar</Link>
        </Button>
      </IfTower>
    ),
  },
];

// Once on each computer where a coding agent works, then once in each checkout.
const LAPTOP_STEPS: Step[] = [
  {
    title: "Install the command",
    text: (
      <>
        You need Python 3.12 or newer. <code className="font-mono">pipx install detente</code>{" "}
        works too.
      </>
    ),
    code: "uv tool install detente",
  },
  {
    title: "Connect each checkout",
    text: (
      <>
        It asks for the agent&apos;s name, your chat username, the tower&apos;s address and the
        pilot token, which is <code className="font-mono">DETENTE_PILOT_TOKEN</code> in the
        tower&apos;s <code className="font-mono">.env</code> file. The address is{" "}
        <code className="font-mono">http://localhost:8100</code> on the tower machine, and
        port 8100 at its <code className="font-mono">TOWER_ADDR</code> from any other laptop.
      </>
    ),
    code: "cd /path/to/your/repo\ndetente connect",
  },
  {
    title: "Keep the watcher running",
    text: "It tells the tower what this checkout's unpushed work changes, while your agent works.",
    code: "detente watch",
  },
  {
    title: "Add the agent to the tower room",
    text: (
      <>
        In Switch, add the agent to the room called tower. It learns the flight-plan rules there.
        If anything seems off, run <code className="font-mono">detente doctor</code>.
      </>
    ),
  },
];

function Code({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto bg-tarmac p-4 font-mono text-[15px] leading-7 text-paint">
      {children}
    </pre>
  );
}

function Steps({ steps }: { steps: Step[] }) {
  return (
    <ol className="grid grid-cols-1 list-decimal gap-20 pl-10 marker:font-display marker:text-3xl marker:font-bold marker:text-runway">
      {steps.map((step) => (
        <li key={step.title} className="rise space-y-3 pl-2">
          <h3 className="display text-3xl">{step.title}</h3>
          <p className="max-w-[60ch] text-lg leading-relaxed">{step.text}</p>
          {step.code && <Code>{step.code}</Code>}
          {step.action}
        </li>
      ))}
    </ol>
  );
}

// The two places Detente runs, as the airfield's black location signs: you are here.
function PlaceSign({
  href,
  title,
  text,
  art,
}: {
  href: string;
  title: string;
  text: string;
  art: ReactNode;
}) {
  return (
    <a
      href={href}
      className="location group grid grid-cols-[1fr_auto] items-center gap-x-6 gap-y-1 p-8 transition-colors hover:bg-raised focus-visible:bg-raised"
    >
      <span className="display text-[clamp(2.5rem,4vw,4rem)] text-runway">{title}</span>
      <span className="row-span-2 transition-transform group-hover:translate-x-1">{art}</span>
      <span className="text-lg">{text}</span>
    </a>
  );
}

export default function GetStartedPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader links={PUBLIC_LINKS}>
        <TowerAction />
      </SiteHeader>

      <main className="flex-1">
        <section
          aria-labelledby="run-title"
          className="grid items-center gap-10 px-4 pt-10 pb-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:pt-16 lg:pb-32"
        >
          <div className="grid justify-items-start gap-6 lg:col-span-7">
            <h1 id="run-title" className="display text-[clamp(3.5rem,9vw,9.5rem)]">
              Run Detente yourself
            </h1>
            <p className="max-w-[46ch] text-xl leading-relaxed">
              Detente runs on your own computers. One machine runs the tower, and each laptop gets
              the <code className="font-mono text-[0.9em]">detente</code> command.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button asChild size="lg">
                <a href={REPO_URL}>Get the code</a>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/showcase">Play the showcase first</Link>
              </Button>
            </div>
          </div>
          <nav aria-label="On this page" className="grid gap-4 lg:col-span-5">
            <PlaceSign
              href="#tower"
              title="The tower"
              text="One machine, for the whole team"
              art={<RogerBadge mood="watching" scale={4} />}
            />
            <PlaceSign
              href="#laptops"
              title="Each laptop"
              text="Every computer where an agent works"
              art={
                <span className="grid gap-2">
                  <Plane owner="lay" status="cleared" scale={3} label="Lay's agent" />
                  <Plane owner="a" status="cleared" scale={3} label="A teammate's agent" />
                </span>
              }
            />
          </nav>
        </section>

        <section
          id="tower"
          aria-labelledby="tower-title"
          className="grid scroll-mt-8 grid-cols-1 gap-10 bg-panel px-4 py-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:py-32"
        >
          <figure className="rise-3 m-0 grid content-start gap-3 lg:sticky lg:top-8 lg:col-span-5 lg:self-start">
            <Image
              src="/photos/sfo-control-tower-at-night.jpg"
              alt="San Francisco airport's control tower at night, its glass core lit blue above the terminal"
              width={1920}
              height={2560}
              sizes="(min-width: 1024px) 40vw, 100vw"
              className="aspect-[4/5] h-auto w-full object-cover object-top"
            />
            <figcaption className="text-[15px]">
              The control tower at San Francisco airport. Yours is one computer that stays on.
            </figcaption>
          </figure>
          <div className="grid grid-cols-1 content-start gap-10 lg:col-span-7">
            <div className="grid gap-4">
              <h2 id="tower-title" className="rise display text-[clamp(3rem,6vw,6rem)]">
                The tower
              </h2>
              <p className="rise-2 max-w-[56ch] text-xl leading-relaxed">
                One machine runs Switch, Detente and the radar for the whole team. Someone sets it
                up once.
              </p>
            </div>
            <Steps steps={TOWER_STEPS} />
          </div>
        </section>

        <section
          id="laptops"
          aria-labelledby="laptops-title"
          className="grid scroll-mt-8 grid-cols-1 gap-10 px-4 py-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:py-32"
        >
          <div className="grid grid-cols-1 content-start gap-10 lg:col-span-6">
            <div className="grid gap-4">
              <h2 id="laptops-title" className="rise display text-[clamp(3rem,6vw,6rem)]">
                Each laptop
              </h2>
              <p className="rise-2 max-w-[56ch] text-xl leading-relaxed">
                Every computer where a coding agent works. Nobody signs in here: the{" "}
                <code className="font-mono text-[0.9em]">detente</code> command uses the pilot
                token.
              </p>
            </div>
            <Steps steps={LAPTOP_STEPS} />
          </div>
          <div className="grid content-start gap-10 lg:sticky lg:top-8 lg:col-span-6 lg:self-start">
            <figure className="rise-3 m-0 grid gap-3">
              <Image
                src="/cli/home.png"
                alt="detente in a connected checkout: Roger, lay-claude on its checkout, the latest from the tower, and the six commands you'll use most"
                width={2084}
                height={928}
                sizes="(min-width: 1024px) 48vw, 100vw"
                className="h-auto w-full"
              />
              <figcaption className="text-[15px]">
                <code className="font-mono">detente</code> in a connected checkout: who this agent
                is, the latest from the tower, and the commands you&apos;ll use most.
              </figcaption>
            </figure>
            <figure className="rise-3 m-0 grid gap-3">
              <Image
                src="/cli/doctor.png"
                alt="detente doctor with every check passed: Python, git, the checkout, connected as lay-claude, the commit gate, the Claude Code edit gate and the tower"
                width={2084}
                height={440}
                sizes="(min-width: 1024px) 48vw, 100vw"
                className="h-auto w-full"
              />
              <figcaption className="text-[15px]">
                <code className="font-mono">detente doctor</code> once a laptop is set up: both
                gates on and the tower answering.
              </figcaption>
            </figure>
          </div>
        </section>

        <section
          aria-labelledby="chat-title"
          className="grid gap-10 bg-panel px-4 py-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:py-32"
        >
          <div className="grid content-start gap-6 lg:col-span-5">
            <h2 id="chat-title" className="rise display text-[clamp(3rem,6vw,6rem)]">
              Then you decide in chat
            </h2>
            <p className="rise-2 text-xl leading-relaxed">
              When one agent&apos;s change breaks code another is writing, Detente holds both and
              opens a conflict room in Switch. Reply A or B there, and the agent you picked makes
              the fix.
            </p>
            <Link
              href="/showcase"
              className="rise-3 flex min-h-40 flex-col justify-between gap-6 bg-runway p-6 text-tarmac transition-colors hover:bg-paint"
            >
              <span className="display text-3xl">See one happen in the showcase</span>
              <span className="self-end text-6xl">
                <SignArrow />
              </span>
            </Link>
          </div>
          <figure className="rise-3 m-0 grid content-start gap-3 lg:col-span-7">
            <Image
              src="/cli/conflict.png"
              alt="detente conflict in a terminal: total_due gained a currency argument, statement.py still calls it the old way, fixes A and B, and the pick"
              width={2182}
              height={684}
              sizes="(min-width: 1024px) 55vw, 100vw"
              className="h-auto w-full"
            />
            <figcaption className="text-[15px]">
              A real conflict, as <code className="font-mono">detente conflict</code> shows it:
              what changed, what it breaks, the two fixes, and the pick made in chat.
            </figcaption>
          </figure>
        </section>
      </main>

      <footer className="bg-panel px-4 pb-8 text-sm leading-relaxed text-dim sm:px-6 lg:px-8">
        Picture:{" "}
        <a
          href="https://commons.wikimedia.org/wiki/File:SFO_Control_tower,_night._(28125162268).jpg"
          className="underline underline-offset-2"
        >
          SFO Control tower, night
        </a>{" "}
        by mliu92, CC BY-SA 2.0, via Wikimedia Commons.
      </footer>
    </div>
  );
}
