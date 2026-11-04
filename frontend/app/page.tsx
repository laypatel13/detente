import Image from "next/image";
import Link from "next/link";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { Roger } from "@/components/sprite";
import { Button } from "@/components/ui/button";
import bench from "@/lib/bench.json";
import realMerges from "@/lib/real-merges.json";
import { cn } from "@/lib/utils";
import { HeroRadar } from "./_landing/hero-radar";
import { type Result, ScenarioMatrix } from "./_landing/scenario-matrix";
import { SameEdits } from "./_landing/same-edits";
import { Stages } from "./_landing/stages";
import { SwitchStory } from "./_landing/switch-story";
import { HERO_FRAMES } from "./hero-frame";

// `make bench` writes this file, so the table always matches the last run.
const SCENARIOS = bench.scenarios as { name: string; breaks: boolean; results: Result[] }[];
const BREAKS = SCENARIOS.filter((scenario) => scenario.breaks);
const SAFE = SCENARIOS.filter((scenario) => !scenario.breaks);
const count = (rows: typeof SCENARIOS, tool: number, result: Result) =>
  rows.filter((scenario) => scenario.results[tool] === result).length;

const TOOLS = ["git merge-tree", "File leases", "Detente"];
const DETENTE = 2;

// `make bench-real` writes this file from merges that really shipped.
const PROJECTS = realMerges.projects;
const sum = (pick: (project: (typeof PROJECTS)[number]) => number) =>
  PROJECTS.reduce((total, project) => total + pick(project), 0);
const REAL = {
  replayed: sum((project) => project.replayed),
  conflicted: sum((project) => project.conflicted),
  caught: sum((project) => project.caught),
  clean: sum((project) => project.clean),
  falseStops: sum((project) => project.false_stops),
};

const listOf = (names: string[]) =>
  names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names.join("");

// The number leads and says what it counts right under it.
function Score({ value, label }: { value: number; label: string }) {
  return (
    <span className="grid">
      <span className="display text-5xl sm:text-7xl">{value}</span>
      <span className="text-base font-medium sm:text-lg">{label}</span>
    </span>
  );
}

const CREDITS = [
  {
    title: "Ben Gurion International Airport taxiway signs",
    href: "https://commons.wikimedia.org/wiki/File:Ben_Gurion_International_Airport_taxiway_signs.JPG",
    by: "My another account",
    licence: "CC0",
  },
  {
    title: "Ben Gurion International Airport 4 taxiway signs",
    href: "https://commons.wikimedia.org/wiki/File:Ben_Gurion_International_Airport_4_taxiway_signs.JPG",
    by: "My another account",
    licence: "CC0",
  },
  {
    title: "Flight control strip at Jakarta control",
    href: "https://commons.wikimedia.org/wiki/File:Flight_control_strip_at_Jakarta_control.jpg",
    by: "Fred775",
    licence: "public domain",
  },
];

function SignArrow({ flip = false }: { flip?: boolean }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={`size-[1em] shrink-0 ${flip ? "-scale-x-100" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="7"
      aria-hidden
    >
      <path d="M4 24h38M26 8l16 16-16 16" />
    </svg>
  );
}

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <section aria-label="Detente" className="flex min-h-svh flex-col bg-runway text-tarmac">
        <SiteHeader links={PUBLIC_LINKS}>
          <Link
            href="/login"
            className="hidden text-lg font-medium underline-offset-4 hover:underline focus-visible:underline sm:inline"
          >
            Sign in
          </Link>
        </SiteHeader>

        <div className="sign-array">
          <h1 className="sign-title display">
            <span>Traffic control</span> <span>for coding agents</span>
          </h1>

          <div className="note-left grid justify-items-start gap-5">
            <p className="text-xl leading-snug font-medium">
              Detente catches collisions between your team&apos;s agents before anyone pushes, and
              a person picks the fix.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button asChild size="lg" variant="ink">
                <Link href="/showcase">Play the showcase</Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="hover:border-tarmac hover:bg-tarmac hover:text-runway"
              >
                <Link href="/get-started">Set it up</Link>
              </Button>
            </div>
          </div>

          <figure className="location m-0 flex min-w-0 flex-col justify-center gap-1">
            <HeroRadar frames={HERO_FRAMES} />
          </figure>

          <p className="note-right text-xl leading-snug font-medium">
            Detente: when rivals stop fighting.
          </p>
        </div>
      </section>

      <main className="flex-1">
        <section
          aria-labelledby="locks-title"
          className="bg-sky px-4 py-24 sm:px-6 lg:px-8 lg:py-32"
        >
          <div className="grid gap-6">
            <h2 id="locks-title" className="rise display text-[clamp(2.25rem,5.4vw,6rem)]">
              File locks catch the wrong conflicts
            </h2>
            <p className="rise-2 max-w-[72ch] text-lg leading-relaxed lg:text-xl">
              The expensive ones live in different files. One agent adds a required argument to{" "}
              <code className="font-mono text-base">create_session</code>. Another, on a different
              laptop, writes code that still calls it the old way. Neither has pushed. Try the same
              two edits against each check.
            </p>
          </div>
          <SameEdits />
        </section>

        <section
          aria-labelledby="airfields-title"
          className="grid bg-paint text-tarmac lg:grid-cols-[7fr_5fr]"
        >
          <figure className="relative m-0 min-h-[20rem] overflow-hidden lg:min-h-[44rem]">
            <Image
              src="/photos/ben-gurion-international-airport-4-taxiway-signs.jpg"
              alt="Yellow, black and red taxiway signs beside painted lines on an airfield"
              fill
              sizes="(min-width: 1024px) 58vw, 100vw"
              className="object-cover object-[80%_100%]"
            />
          </figure>
          <div className="grid content-center gap-6 p-6 sm:p-10 lg:p-12">
            <h2 id="airfields-title" className="rise display text-[clamp(2.75rem,5vw,5rem)]">
              Airfields solved this first
            </h2>
            <p className="rise-2 text-lg leading-relaxed">
              Pilots can&apos;t see each other&apos;s plans either. So every flight files one, a
              tower watches every path, and a red sign means hold until someone clears you. Detente
              runs your team&apos;s agents the same way.
            </p>
            <figure className="rise-3 m-0 grid gap-2">
              <Image
                src="/photos/taxiway-sign-array.jpg"
                alt="One airfield sign with a yellow direction panel, a black location panel and a red runway panel"
                width={900}
                height={300}
                sizes="(min-width: 1024px) 38vw, 100vw"
                className="h-auto w-full"
              />
              <figcaption className="text-[15px]">
                Yellow points the way, black says where you are, red means hold.
              </figcaption>
            </figure>
            <figure className="rise-3 m-0 grid gap-2">
              <Image
                src="/photos/flight-control-strip-at-jakarta-control.jpg"
                alt="A rack of paper flight strips at Jakarta air traffic control"
                width={1152}
                height={864}
                sizes="(min-width: 1024px) 38vw, 100vw"
                className="aspect-[3/1] h-auto w-full object-cover object-[50%_72%]"
              />
              <figcaption className="text-[15px]">
                A flight strip rack: one strip for every aircraft.
              </figcaption>
            </figure>
          </div>
        </section>

        <Stages />

        <section
          aria-labelledby="switch-title"
          className="bg-paint px-4 pt-24 pb-12 text-tarmac sm:px-6 lg:px-8 lg:pt-32"
        >
          <div className="grid gap-6">
            <h2 id="switch-title" className="rise display text-[clamp(2.25rem,5.4vw,6rem)]">
              Agents can&apos;t see each other without Switch
            </h2>
            <p className="rise-2 max-w-[72ch] text-lg leading-relaxed lg:text-xl">
              Detente runs as an agent in your team&apos;s chat, on Switch. That&apos;s how it
              works across laptops, and it&apos;s where people make the call.
            </p>
          </div>
          <SwitchStory />
        </section>

        <section
          aria-labelledby="bench-title"
          className="bg-runway px-4 py-24 text-tarmac sm:px-6 lg:px-8 lg:py-32"
        >
          <div className="grid gap-6">
            <h2 id="bench-title" className="rise display text-[clamp(2.25rem,5.4vw,6rem)]">
              {BREAKS.length} real breaks. Merge checks stop {count(BREAKS, 0, "flagged")}.
            </h2>
            <p className="rise-2 max-w-[72ch] text-lg leading-relaxed font-medium lg:text-xl">
              {SCENARIOS.length} scenarios on real git checkouts, offline, with{" "}
              <code className="font-mono text-base">make bench</code>. Detente stops{" "}
              {count(BREAKS, 2, "stop")} and warns on {count(BREAKS, 2, "heads-up")}, and stops{" "}
              {count(SAFE, 2, "stop")} of the {SAFE.length} that are fine. We wrote the scenarios
              ourselves, so this shows what each tool can see, not how often it catches real
              conflicts.
            </p>
          </div>

          <div className="mt-12 grid gap-x-12 gap-y-16 lg:grid-cols-[7fr_5fr]">
            <div className="rise-2 bg-tarmac p-4 text-paint sm:p-8">
              <table aria-label="How many scenarios each check stops" className="w-full text-left max-sm:block">
                {/* On a phone each check gets its own line, with its two numbers side by side. */}
                <tbody className="max-sm:grid max-sm:gap-6">
                  {TOOLS.map((tool, index) => {
                    const mark = index === DETENTE ? "stop" : "flagged";
                    return (
                      <tr
                        key={tool}
                        className={cn(
                          "max-sm:grid max-sm:grid-cols-2 max-sm:gap-x-4",
                          index === DETENTE && "text-runway",
                        )}
                      >
                        <th scope="row" className="display py-4 pr-3 align-top text-2xl max-sm:col-span-2 max-sm:p-0 sm:text-3xl">
                          {tool}
                        </th>
                        <td className="py-4 pr-3 align-top max-sm:p-0">
                          <Score
                            value={count(BREAKS, index, mark)}
                            label={`of ${BREAKS.length} real breaks stopped`}
                          />
                          {index === DETENTE && (
                            <span className="block text-base text-paint">
                              and {count(BREAKS, DETENTE, "heads-up")} more warned about
                            </span>
                          )}
                        </td>
                        <td className="py-4 align-top max-sm:p-0">
                          <Score
                            value={count(SAFE, index, mark)}
                            label={`of ${SAFE.length} fine changes stopped`}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="rise-2 grid content-start gap-5">
              <h3 className="display text-[clamp(2rem,3.2vw,3rem)]">
                Then {REAL.replayed} real merges
              </h3>
              <p className="text-lg leading-relaxed font-medium lg:text-xl">
                Merged pull requests from {listOf(PROJECTS.map((project) => project.name))},
                replayed through the real laptop daemon with both sides at once. Git conflicted
                on {REAL.conflicted}. Detente stopped{" "}
                {REAL.caught === REAL.conflicted ? "all" : REAL.caught} {REAL.conflicted}, and{" "}
                {REAL.falseStops || "none"} of the {REAL.clean} that merged cleanly.
              </p>
              <p className="text-lg leading-relaxed">
                Breaks git misses rarely survive in a project&apos;s history, so this measures
                false alarms, not catches. Try it on yours with{" "}
                <code className="font-mono text-base whitespace-nowrap">make bench-real</code>.
              </p>
            </div>
          </div>

          <div className="rise-2 mt-12 bg-tarmac p-4 text-paint sm:p-8">
            <h3 className="sr-only">Every scenario, check by check</h3>
            <ScenarioMatrix scenarios={SCENARIOS} />
          </div>
          <p className="mt-10 max-w-[70ch] text-lg leading-relaxed font-medium">
            Calls are checked in Python only for now; other files are checked line by line, as
            git would merge them. A change in what a function does, like a renamed dict key, only
            gets a heads-up, and that depends on agents declaring the overlap honestly.
          </p>
        </section>

        <section
          aria-labelledby="tower-title"
          className="grid min-h-svh grid-rows-[auto_1fr_auto] justify-items-center bg-tarmac px-4 py-6 text-center"
        >
          <h2 id="tower-title" className="contents">
            <span className="display block text-[clamp(5rem,16vw,15rem)] text-runway">Take the</span>
            <span className="row-start-3 display block text-[clamp(5rem,16vw,15rem)] text-runway">
              tower
            </span>
          </h2>
          <div className="row-start-2 grid content-center justify-items-center gap-4 py-8">
            <Roger mood="watching" scale={7} />
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-6">
              <Button asChild size="lg">
                <Link href="/showcase">Play the showcase</Link>
              </Button>
              <span className="text-lg text-dim">or</span>
              <Button asChild size="lg">
                <Link href="/get-started">Set it up</Link>
              </Button>
            </div>
            <p className="text-dim">
              The showcase needs no sign-in. The real thing runs on your team&apos;s own machines.
            </p>
          </div>
        </section>
      </main>

      <footer className="bg-sky px-4 py-8 sm:px-6 lg:px-8 lg:pt-12">
        {/* An airfield sign pair: where you are, and which way to go. */}
        <div className="grid lg:grid-cols-12">
          <div className="location flex items-center justify-center py-6 lg:col-span-8 lg:min-h-80">
            <p className="display text-[clamp(4rem,13vw,13rem)] text-runway">Detente</p>
          </div>
          <Link
            href="/showcase"
            className="flex min-h-48 flex-col justify-between bg-runway p-6 text-tarmac transition-colors hover:bg-paint lg:col-span-4"
          >
            <span className="display text-4xl">Play the showcase</span>
            <span className="self-end text-7xl">
              <SignArrow />
            </span>
          </Link>
        </div>

        <div className="mt-8 grid items-baseline gap-x-8 gap-y-4 lg:grid-cols-12">
          <p className="text-lg leading-snug lg:col-span-5">
            The radar only shows what&apos;s happening. Every decision stays in chat, on Switch.
          </p>
          <nav aria-label="Footer" className="lg:col-span-3">
            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-lg">
              <li>
                <Link href="/showcase" className="underline-offset-4 hover:underline">
                  Showcase
                </Link>
              </li>
              <li>
                <Link href="/get-started" className="underline-offset-4 hover:underline">
                  Set up
                </Link>
              </li>
              <li>
                <Link href="/login" className="underline-offset-4 hover:underline">
                  Sign in
                </Link>
              </li>
            </ul>
          </nav>
          <p className="text-sm leading-relaxed text-dim lg:col-span-4">
            Pictures:{" "}
            {CREDITS.map((credit, index) => (
              <span key={credit.href}>
                {index > 0 && "; "}
                <a href={credit.href} className="underline underline-offset-2">
                  {credit.title}
                </a>{" "}
                by {credit.by}, {credit.licence}
              </span>
            ))}
            , via Wikimedia Commons.
          </p>
        </div>
      </footer>
    </div>
  );
}
