import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import {
  CODE_FONT,
  Code,
  CommandShelf,
  type Shelf,
  TowerField,
  TowerLink,
  TowerProvider,
} from "@/components/docs-live";
import { SignArrow } from "@/components/sign-arrow";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { RogerBadge } from "@/components/sprite";
import { REPO_URL, TowerAction } from "@/components/tower";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Docs",
  description:
    "How Detente catches a break between coding agents, how to run it, every command and chat phrase, and what it can't do yet.",
};

// The handbook's one shape is the airfield sign: the contents are a sign array, every chat phrase is
// set on its sign, and the page closes on the name built from signs.

const PLACES = [
  { id: "how", label: "How it works" },
  { id: "run", label: "Run it" },
  { id: "commands", label: "Commands" },
  { id: "chat", label: "Talk to Detente" },
  { id: "benchmark", label: "Benchmark" },
  { id: "switch", label: "Under the hood" },
  { id: "limits", label: "Limits" },
];

// The six stages, darkest first: one hue, the runway's yellow, getting lighter as a flight
// gets closer to landing.
const STAGES = [
  {
    name: "File a flight plan",
    line: "FLIGHT PLAN\ntask: add a timeout to sessions\nedit: auth/session.py\nchanges: create_session",
    tone: "#2b2408",
    text: "Before it edits anything, an agent posts what it will change in the tower room.",
  },
  {
    name: "Get cleared",
    line: "[o_o] CLEARED lay-claude · auth/session.py",
    tone: "#4a3d0b",
    text: "Detente clears the plan, and warns when it overlaps someone else's.",
  },
  {
    name: "Gates enforce it",
    line: "No clearance for billing/models.py. File a flight plan in the tower room.",
    tone: "#6f5a0e",
    text: "A Claude Code hook refuses edits, and a git hook refuses commits, for any file not cleared. Shell commands are checked for files they changed.",
  },
  {
    name: "Squawks report the code",
    line: "lay-claude  auth/session.py\n            def create_session(user, ttl)\na-codex     billing/refunds.py:42\n            create_session(user)",
    tone: "#9a7c11",
    dark: true,
    text: "A daemon on each laptop sends the signatures that changed and the calls being made in unpushed work. Detente compares them across laptops with Python's ast, and fetches main every 10 seconds while there's unpushed work.",
  },
  {
    name: "A break holds both",
    line: "Holding for conflict-create-session-3f1a. A person decides in that room.",
    tone: "#c99f14",
    dark: true,
    text: "When one agent's change breaks code the other is writing, Detente holds both flights and opens a conflict room with both people and both agents.",
  },
  {
    name: "A person picks A or B",
    line: "lay: A\n[^_^] DECIDED by lay (A): pass a ttl in billing/refunds.py. a-codex makes the edit.\n[^_^] RESOLVED conflict-create-session-3f1a: the code fits again. 0 open collisions.",
    tone: "#ffc417",
    dark: true,
    text: "The holds lift, the agent you picked makes the fix, and Detente archives the room once the code fits again.",
  },
];

const COLLISION = `[O_O]! COLLISION lay-claude changed create_session(user) to create_session(user, ttl)
a-codex's billing/refunds.py:42 is missing required argument ttl
Nothing pushed. Both flights holding.
Opened conflict-create-session-3f1a.`;

const ADDRESSES = [
  { what: "Radar, after you sign in", port: 3100, path: "/radar" },
  { what: "Showcase", port: 3100, path: "/showcase" },
  { what: "Detente's API", port: 8100, path: "" },
  { what: "Mattermost, for chat", port: 8065, path: "" },
  { what: "Switch Gateway", port: 3110, path: "" },
  { what: "Switch's agent API", port: 8110, path: "" },
];

const mono = (text: string) => (
  <code className={`${CODE_FONT} [overflow-wrap:anywhere]`}>{text}</code>
);

// The rows of real tables keep their lines.
const ROW = "border-t border-[var(--line)]"; // taste-skill-ignore: rows of real tables

const SHELVES: Shelf[] = [
  {
    name: "Start",
    picture: "home",
    rows: [
      {
        cmd: "detente",
        does: "Roger, where you are, and the commands you'll use most.",
      },
      {
        cmd: "detente connect",
        does: "Connects the checkout you're in to your team's tower: the commit gate, Claude Code's edit gate, the callsign and the pilot token.",
      },
      {
        cmd: "detente watch",
        does: "Tells the tower what this checkout's unpushed work changes and calls. While there's unpushed work it also fetches main every 10 seconds. Ctrl+C stops it.",
      },
      {
        cmd: "detente doctor",
        does: "Checks git, the config, both gates, and that the tower answers and takes the token.",
      },
      {
        cmd: "detente disconnect",
        does: "Removes this checkout's gates and config. Other hooks, your code and your commits stay as they are.",
      },
    ],
  },
  {
    name: "The tower",
    picture: "conflict",
    rows: [
      {
        cmd: "detente status",
        does: (
          <>
            Flights in the air, open conflicts and the latest messages.{" "}
            {mono("-n 10")} shows more.
          </>
        ),
      },
      {
        cmd: "detente conflict [name]",
        does: "One conflict in full: what changed, what it breaks, the fixes on offer and who picked. Leave the name out for the open one.",
      },
      {
        cmd: "detente check <file>…",
        does: "Is this checkout cleared to edit these files? Exits 1 if any isn't. For agents without Claude Code's hooks, and for scripts.",
      },
    ],
  },
  {
    name: "Options and exit codes",
    picture: "doctor",
    rows: [
      {
        cmd: "--repo PATH, -r PATH",
        does: "Use another checkout than the one you're in.",
      },
      {
        cmd: "--json",
        does: (
          <>
            The raw result as JSON, for scripts: {mono("doctor")},{" "}
            {mono("status")}, {mono("conflict")} and {mono("check")}.
          </>
        ),
      },
      { cmd: "exit 0", does: "All fine." },
      { cmd: "exit 1", does: <>A finding: {mono("check")} refused a file.</> },
      { cmd: "exit 2", does: "A usage problem." },
      {
        cmd: "exit 3",
        does: (
          <>
            The setup or the tower: {mono("doctor")} found a problem, or the
            tower didn&apos;t answer.
          </>
        ),
      },
    ],
  },
  {
    name: "Showcase",
    rows: [
      {
        cmd: "detente showcase",
        does: (
          <>
            The recorded run, in your terminal. {mono("--fast")} plays it
            without pauses.
          </>
        ),
      },
      {
        cmd: "uvx detente showcase",
        does: "The same, with nothing installed but uv.",
      },
    ],
  },
  {
    name: "Accounts, on the tower machine",
    rows: [
      {
        cmd: "add <name>",
        does: "Adds an account. It asks for a password of at least 12 characters.",
      },
      {
        cmd: "password <name>",
        does: "Changes the password and signs that person out everywhere.",
      },
      {
        cmd: "remove <name>",
        does: "Removes the account and ends its sessions at once.",
      },
      { cmd: "list", does: "Lists accounts." },
    ],
    note: (
      <>
        Run each one after{" "}
        {mono(
          "docker compose -p detente exec api .venv/bin/python -m backend.accounts",
        )}
        . Five wrong passwords lock that name for five minutes. Sessions last 14
        days.
      </>
    ),
  },
  {
    name: "Develop",
    rows: [
      {
        cmd: "make test",
        does: "Everything offline. Fails if the real app imports showcase code.",
      },
      {
        cmd: "make bench",
        does: "32 scenarios on real git checkouts, in seconds.",
      },
      {
        cmd: 'make bench-real REPOS="…"',
        does: "Replays merged PRs from a project's history to count false alarms.",
      },
      { cmd: "make dev", does: "The API and the web app with live reload." },
      {
        cmd: "make test-live",
        does: "Real Switch, Mattermost, git worktrees, gates and squawk daemons. Needs Switch and Detente running.",
      },
      {
        cmd: "make test-crash",
        does: "Kills Detente mid-collision to prove holds survive a crash. Needs make api.",
      },
      {
        cmd: "make record",
        does: "Flies both choices on real Switch and rewrites the showcase's recordings.",
      },
    ],
  },
];

const PICTURES = {
  home: {
    src: "/cli/home.png",
    width: 2050,
    height: 928,
    alt: "detente in a connected checkout: Roger, lay-claude on its checkout, the latest from the tower, and the commands you'll use most",
  },
  conflict: {
    src: "/cli/conflict.png",
    width: 2146,
    height: 684,
    alt: "detente conflict: total_due gained a currency argument, statement.py still calls it the old way, fixes A and B, and the pick",
  },
  doctor: {
    src: "/cli/doctor.png",
    width: 2050,
    height: 440,
    alt: "detente doctor with every check passed: Python, git, the checkout, the callsign, both gates and the tower",
  },
};

const PHRASES: {
  who: string;
  says: string;
  kind: "hold" | "cleared" | "traffic" | "plain";
  does: string;
}[] = [
  {
    who: "A person",
    says: "@detente ground stop",
    kind: "hold",
    does: "Every gate closes until resume.",
  },
  {
    who: "A person",
    says: "@detente resume",
    kind: "cleared",
    does: "Gates reopen.",
  },
  {
    who: "A person",
    says: "@detente land <callsign>",
    kind: "plain",
    does: "Clears that flight and stops comparing its unpushed work, for an agent that died or a break you accept.",
  },
  {
    who: "A person",
    says: "A or B",
    kind: "traffic",
    does: "In a conflict room, picks the fix.",
  },
  {
    who: "An agent",
    says: "FLIGHT PLAN",
    kind: "plain",
    does: "Files a plan.",
  },
  {
    who: "An agent",
    says: "LANDED",
    kind: "cleared",
    does: "Closes its flight. Its work still counts, unpushed or just pushed.",
  },
];

const SWITCH = [
  [
    "Rooms across laptops and vendors",
    "Every pilot sees the tower room. This is how agents on different machines see each other.",
  ],
  [
    "Agent protocol",
    "Detente is a custom always-on agent: one event stream per room, HTTP operations out.",
  ],
  [
    "send_targeted_message",
    "Addresses clearances, holds and decisions to the exact pilots involved.",
  ],
  [
    "create_room, link_rooms",
    "Opens a conflict room with both people and both agents, linked to the tower room both ways.",
  ],
  ["archive_room", "Archives a conflict room when it's resolved."],
  [
    "Room documents",
    "Keeps the live Airspace board. Read it with !list-documents.",
  ],
  [
    "Room instructions",
    "Teaches every pilot the flight-plan rules when it joins.",
  ],
  [
    "Exclusive role",
    "Detente holds the tower role, so there's only ever one controller.",
  ],
  ["read_context", "Catches up on anything said while Detente was down."],
];

// The limits, filed by topic. Each card is one drawer of the same cabinet.
const LIMITS: { topic: string; question: string; items: ReactNode[] }[] = [
  {
    topic: "Reading code",
    question: "What can't it see in the code?",
    items: [
      <>
        Calls are checked in Python only. Other files are checked line by line,
        the way git would merge them, so a clash in {mono("package.json")} is
        caught but a broken call in TypeScript isn&apos;t.
      </>,
      <>
        Methods resolve only through types Detente can see.{" "}
        {mono("store.open()")} is checked when {mono("store")} comes from{" "}
        {mono("SessionStore()")}, an annotation or an attribute set on{" "}
        {mono("self")}; an object returned by a function, or an inherited
        method, isn&apos;t.
      </>,
      "Behavior changes are invisible. A renamed dict key or a changed return value fits the signature, so only a flight plan can flag it.",
    ],
  },
  {
    topic: "Comparing",
    question: "When does a comparison fall short?",
    items: [
      "Line clashes need the same starting version. Otherwise any shared change to a function stops both, to be safe.",
      "Only calls your work wrote are checked. A call already on main is the job of whoever changes the function.",
      "A push Detente never saw is credited to main. A person's push names no one, so the agent whose work broke gets both fixes.",
    ],
  },
  {
    topic: "Gates",
    question: "Can the gates be got round?",
    items: [
      <>
        {mono("git commit --no-verify")} skips the commit gate. The edit gate
        covers Claude Code only, so other vendors rely on the commit gate.
      </>,
      "Shell edits are caught after they run. Detente checks what changed once a command finishes and tells the agent to undo anything uncleared.",
      "Gates fail closed. If Detente is unreachable, edits and commits are refused.",
    ],
  },
  {
    topic: "Setup",
    question: "What does one install cover?",
    items: [
      "One repo, one tower room. Multi-repo support isn't built.",
      "Tested on Mattermost only. Detente talks to Switch, never to the chat app, so Slack, Discord and Microsoft Teams should work through Switch, but they haven't been tried. Telegram can't: Switch can't create chats there, so conflict rooms can't open.",
      "One pilot token per install. Every laptop shares it, so anyone holding it can report as any callsign. Keep port 8100 on a private network.",
    ],
  },
  {
    topic: "Network",
    question: "Is it safe across the internet?",
    items: [
      <>
        {mono("TOWER_ADDR")} serves plain HTTP, so share it over Tailscale,
        which encrypts the traffic, or behind an HTTPS proxy that sets{" "}
        {mono("X-Forwarded-Proto")}.
      </>,
      <>
        People get Switch&apos;s owner-only default. {mono("@detente")} commands
        work for anyone in the room, but Switch shows others a refusal until you
        widen its addressing policy in the Gateway.
      </>,
    ],
  },
];

const CARD_TONES = [
  "bg-raised text-ink",
  "bg-runway text-tarmac",
  "bg-paint text-tarmac",
  "bg-panel text-ink",
  "bg-hold text-paint",
];

// The threshold markings at a runway's end: the stripe across the top of the card.
function Threshold() {
  return (
    <div aria-hidden className="flex h-12 gap-0 overflow-hidden">
      {Array.from({ length: 40 }, (_, index) => (
        <span
          key={index}
          className={`h-full w-7 shrink-0 ${index % 2 ? "bg-panel" : "bg-paint"}`}
        />
      ))}
    </div>
  );
}

function Heading({
  id,
  children,
  className = "",
}: {
  id: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <h2
      id={`${id}-title`}
      className={`rise display text-[clamp(3rem,6vw,6rem)] ${className}`}
    >
      {children}
    </h2>
  );
}

function PictureWord({
  src,
  alt,
  position = "center",
}: {
  src: string;
  alt: string;
  position?: string;
}) {
  return (
    <Image
      src={src}
      alt={alt}
      width={240}
      height={126}
      sizes="80px"
      style={{ objectPosition: position }}
      className="mx-[0.12em] inline-block h-[1.2em] w-[2.6em] translate-y-[0.22em] object-cover align-baseline"
    />
  );
}

export default function DocsPage() {
  return (
    <TowerProvider>
      <div className="flex min-h-dvh flex-col">
        <SiteHeader links={PUBLIC_LINKS}>
          <TowerAction />
        </SiteHeader>

        <main className="docs flex-1">
          <section
            aria-labelledby="docs-title"
            className="grid gap-3 px-4 pb-3 sm:px-6 lg:grid-cols-2 lg:gap-8 lg:px-8"
          >
            <div className="grid content-start bg-panel">
              <Threshold />
              <div className="grid content-start justify-items-start gap-8 p-6 sm:p-10 lg:p-12">
                <RogerBadge mood="watching" scale={5} />
                <h1
                  id="docs-title"
                  className="display text-[clamp(3.5rem,8vw,8rem)]"
                >
                  Detente docs
                </h1>
                <p className="max-w-[44ch] text-lg leading-relaxed">
                  Everything in one place: how Detente catches a break, how to
                  run it, every command and chat phrase, and what it can&apos;t
                  do yet.
                </p>
                <TowerField />
                <Button asChild size="lg">
                  <a href="#run">Set it up</a>
                </Button>
              </div>
            </div>
            <figure className="m-0 grid">
              <Image
                src="/photos/ben-gurion-international-airport-4-taxiway-signs.jpg"
                alt="A yellow taxiway direction sign with an arrow pointing left to W2, beside a black location sign marked R, on the apron at Ben Gurion airport"
                width={1606}
                height={1207}
                priority
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="h-[48svh] w-full object-cover object-[78%_82%] lg:h-full lg:min-h-[78svh]"
              />
            </figure>
          </section>

          {/* The contents, as the sign array at a taxiway crossing: where you are, then the way to each part. */}
          <nav
            aria-label="On this page"
            className="px-4 pt-3 pb-24 sm:px-6 lg:px-8 lg:pb-32"
          >
            <ul className="flex flex-wrap gap-1.5">
              <li className="display flex min-h-16 items-center border-4 border-runway bg-tarmac px-5 text-3xl text-runway">
                Docs
              </li>
              {PLACES.map((place) => (
                <li key={place.id} className="flex">
                  <a
                    href={`#${place.id}`}
                    className="display flex min-h-16 items-center gap-3 bg-runway px-5 text-3xl text-tarmac transition-[background-color,transform] hover:bg-paint focus-visible:bg-paint active:translate-y-0.5"
                  >
                    {place.label}
                    <span className="rotate-90 text-[0.8em]">
                      <SignArrow />
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <section
            id="how"
            aria-labelledby="how-title"
            className="grid scroll-mt-8 gap-16 px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28"
          >
            <div className="grid gap-6 lg:grid-cols-12 lg:gap-8">
              <Heading id="how" className="lg:col-span-5">
                How it works
              </Heading>
              <p className="rise-2 max-w-[56ch] self-end text-lg leading-relaxed lg:col-span-6 lg:col-start-7">
                Agents on different laptops can&apos;t see each other&apos;s
                unpushed work, and file locks only catch two edits to one file.
                Detente sits in your team&apos;s chat as the tower, compares
                what each agent is changing, and holds both before a break is
                pushed.
              </p>
            </div>

            <div className="stages rise-3">
              {STAGES.map((stage, index) => (
                <details
                  key={stage.name}
                  name="stage"
                  open={index === 0}
                  className="stage"
                  style={{
                    background: stage.tone,
                    color: stage.dark ? "var(--tarmac)" : "var(--paint)",
                  }}
                >
                  <summary>{stage.name}</summary>
                  <pre className={`stage-line ${CODE_FONT}`}>{stage.line}</pre>
                  <p>{stage.text}</p>
                </details>
              ))}
            </div>

            <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
              <figure className="rise m-0 grid content-start gap-3 lg:col-span-6">
                <a
                  href="/figures/tower.html"
                  className="group relative block focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-runway"
                >
                  <Image
                    src="/figures/tower.png"
                    alt="An airfield model: Roger stands red-faced on the tower with the hold beacon lit, while lay-claude's blue plane and a-codex's orange plane hold in the air short of the runway marked main"
                    width={1640}
                    height={1045}
                    sizes="(min-width: 1024px) 48vw, 100vw"
                    className="h-auto w-full transition-opacity group-hover:opacity-85"
                  />
                  <span className="absolute bottom-3 left-3 inline-flex min-h-11 items-center gap-2 bg-runway px-4 text-base font-medium text-tarmac transition-colors group-hover:bg-paint">
                    <svg aria-hidden="true" viewBox="0 0 12 12" className="size-3 fill-current">
                      <path d="M2 1l9 5-9 5z" />
                    </svg>
                    Play the run
                  </span>
                </a>
                <figcaption className="text-base leading-relaxed">
                  Step 2 of 6 in the run: both flights hold short of main while
                  Roger calls the collision. Tap the picture to play all six
                  steps, from approach to both planes landed.
                </figcaption>
              </figure>
              <div className="rise-2 grid content-start gap-6 lg:col-span-6 lg:col-start-7">
                <h3 className="display text-3xl">What Detente says</h3>
                <p className="text-lg leading-relaxed">
                  lay-claude changed a function. a-codex, on another laptop, is
                  still calling it the old way, in a different file. Nobody has
                  pushed, and no lines overlap.
                </p>
                <Code>{COLLISION}</Code>
                <p className="text-lg leading-relaxed">
                  Every decision is deterministic Python. No LLM call decides a
                  clearance.
                </p>
              </div>
            </div>
          </section>

          <section
            id="run"
            aria-labelledby="run-title"
            className="grid scroll-mt-8 gap-20 bg-panel px-4 py-24 sm:px-6 lg:px-8 lg:py-28"
          >
            <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
              <div className="grid content-start gap-10 lg:col-span-6">
                <Heading id="run">Run it</Heading>
                <p className="rise-2 max-w-[30ch] text-[clamp(1.5rem,2.2vw,1.875rem)] leading-[1.3] font-medium">
                  One computer runs the
                  <PictureWord
                    src="/photos/sfo-control-tower-at-night.jpg"
                    alt=""
                    position="50% 22%"
                  />
                  tower. Each laptop gets the
                  <PictureWord src="/cli/home.png" alt="" position="4% 40%" />
                  command. People decide in
                  <PictureWord
                    src="/photos/flight-control-strip-at-jakarta-control.jpg"
                    alt=""
                    position="50% 40%"
                  />
                  chat.
                </p>
              </div>
              <div className="rise-3 lg:col-span-6 lg:col-start-7 lg:self-end">
                <table className="w-full text-left text-base">
                  <caption className="pb-3 text-left text-lg font-medium">
                    Where everything answers
                  </caption>
                  <tbody>
                    {ADDRESSES.map((row) => (
                      <tr key={row.what} className={ROW}>
                        <th scope="row" className="py-3 pr-4 font-normal">
                          {row.what}
                        </th>
                        <td className="py-3 text-right">
                          <TowerLink
                            href={`http://{tower}:${row.port}${row.path}`}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-20 lg:grid-cols-2 lg:gap-8">
              <div className="grid content-start gap-8">
                <h3 className="rise display text-3xl">The tower</h3>
                <p className="text-lg leading-relaxed">
                  One machine that stays on. You need Docker,{" "}
                  <a
                    href="https://docs.astral.sh/uv/"
                    className="underline underline-offset-4"
                  >
                    uv
                  </a>{" "}
                  and Node 24. This starts Switch with its bundled Mattermost,
                  then Detente and the radar, and makes a sign-in. Switch can{" "}
                  <a
                    href="https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps"
                    className="underline underline-offset-4"
                  >
                    use Slack, Discord or Microsoft Teams
                  </a>{" "}
                  instead, though Detente has only been tested on Mattermost.
                </p>
                <Code>{`git clone ${REPO_URL}\ncd detente\nmake install\nmake switch-up\nmake setup\nmake up\nmake user NAME=yourname`}</Code>
                <h4 className="display text-3xl">
                  Let the team&apos;s laptops in
                </h4>
                <p className="text-lg leading-relaxed">
                  Every address answers on this machine only. Add its address on
                  your team&apos;s private network, such as its{" "}
                  <a
                    href="https://tailscale.com"
                    className="underline underline-offset-4"
                  >
                    Tailscale
                  </a>{" "}
                  address, and restart. Teammates then use it in place of
                  localhost, and Switch&apos;s database stays here.
                </p>
                <Code>
                  {
                    'echo "TOWER_ADDR=100.101.102.103" >> .env\nmake switch-up up'
                  }
                </Code>
                <p className="text-lg leading-relaxed">
                  Already have a Switch server? Skip {mono("make switch-up")}{" "}
                  and run{" "}
                  {mono(
                    "uv run python -m backend.setup --url <agent API URL> --registration-token <token>",
                  )}
                  .
                </p>
              </div>

              <div className="grid content-start gap-8">
                <h3 className="rise display text-3xl">Each laptop</h3>
                <p className="text-lg leading-relaxed">
                  Every computer where an agent works. First,{" "}
                  <a
                    href="https://docs.switchagents.ai/switch-rooms/getting-started/install-switch-console"
                    className="underline underline-offset-4"
                  >
                    Switch Console
                  </a>
                  , Switch&apos;s desktop app, runs the agent and puts it in the
                  team&apos;s chat. When it asks for a server, choose Connect to
                  an existing server and enter this address.
                </p>
                <Code>{"http://{tower}:8110"}</Code>
                <p className="text-lg leading-relaxed">
                  Then install the command once, with Python 3.12 or newer.{" "}
                  {mono("pipx install detente")} works too; {mono("uvx")}{" "}
                  doesn&apos;t, because the gates run from wherever the command
                  is installed.
                </p>
                <Code>uv tool install detente</Code>
                <p className="text-lg leading-relaxed">
                  Then connect each checkout an agent works in. It asks for
                  anything you leave out, including the pilot token,{" "}
                  {mono("DETENTE_PILOT_TOKEN")} in the tower&apos;s{" "}
                  {mono(".env")}, and checks it with the tower before writing
                  anything.
                </p>
                <Code>
                  {
                    'detente connect --callsign lay-claude --person lay --vendor "Claude Code" --url http://{tower}:8100'
                  }
                </Code>
                <p className="text-lg leading-relaxed">
                  Keep the watcher running while agents work, and check the
                  setup whenever something seems off.
                </p>
                <Code>{"detente watch\ndetente doctor"}</Code>
                <p className="text-lg leading-relaxed">
                  Last, set up the agent in Switch Console. Name it exactly the
                  callsign you gave {mono("detente connect")} and point it at
                  this checkout&apos;s folder. Under Who can talk to your agent,
                  add a rule for the agent {mono("detente")}: the default, you
                  and your agents, blocks its clearances and holds. Then add it
                  to the tower room, where it learns the flight-plan rules.
                </p>
                <p className="text-lg leading-relaxed">
                  {mono("connect")} keeps its {mono(".detente")} file out of
                  git. {mono("watch")} sends the paths, changed lines,
                  signatures and calls of your unpushed work, never whole files,
                  and only to your tower. The CLI sends no telemetry.
                </p>
                <Link
                  href="/get-started"
                  className="flex items-center justify-between gap-6 bg-runway p-6 text-tarmac transition-colors hover:bg-paint"
                >
                  <span className="display text-3xl">
                    The set-up walkthrough
                  </span>
                  <span className="text-4xl">
                    <SignArrow />
                  </span>
                </Link>
              </div>
            </div>
          </section>

          <section
            id="commands"
            aria-labelledby="commands-title"
            className="grid scroll-mt-8 gap-6 px-4 py-24 sm:px-6 lg:px-8 lg:py-28"
          >
            <div className="grid lg:grid-cols-12 lg:gap-8">
              <h2
                id="commands-title"
                className="rise display commands-word leading-[0.8] lg:col-span-7"
              >
                Commands
              </h2>
            </div>
            <CommandShelf shelves={SHELVES} pictures={PICTURES} />
          </section>

          <section
            id="chat"
            aria-labelledby="chat-title"
            className="grid scroll-mt-8 gap-10 bg-panel px-4 py-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:py-28"
          >
            <Heading id="chat" className="lg:col-span-12">
              Talk to Detente
            </Heading>
            <div className="grid content-start gap-6 lg:col-span-4">
              <p className="rise-2 text-lg leading-relaxed">
                Decisions happen in Switch, where both people and both agents
                see them. The CLI never picks a fix. Detente checks that the
                sender is a person before it acts.
              </p>
            </div>
            <table className="rise-3 w-full text-left max-md:block lg:col-span-8">
              <caption className="sr-only">
                What people and agents say to Detente, and what happens
              </caption>
              <thead className="max-md:hidden">
                <tr className="text-base text-dim">
                  <th scope="col" className="pb-4 font-medium">
                    Says
                  </th>
                  <th scope="col" className="pb-4 pl-6 font-medium">
                    Who
                  </th>
                  <th scope="col" className="pb-4 pl-6 font-medium">
                    What happens
                  </th>
                </tr>
              </thead>
              <tbody className="max-md:grid max-md:gap-2">
                {PHRASES.map((phrase) => (
                  <tr
                    key={phrase.says}
                    className={`${ROW} align-top max-md:grid max-md:grid-cols-[auto_1fr] max-md:gap-x-4 max-md:pt-5`}
                  >
                    <td className="py-5 max-md:col-span-2 max-md:pt-0 max-md:pb-3">
                      <span
                        className="sign text-3xl max-md:text-2xl max-md:whitespace-normal"
                        data-kind={phrase.kind}
                      >
                        {phrase.says}
                      </span>
                    </td>
                    <td className="py-5 pl-6 text-lg whitespace-nowrap max-md:p-0 max-md:text-dim">
                      {phrase.who}
                    </td>
                    <td className="py-5 pl-6 text-lg leading-relaxed max-md:p-0">
                      {phrase.does}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section
            id="benchmark"
            aria-labelledby="benchmark-title"
            className="grid scroll-mt-8 gap-2 px-4 py-24 sm:px-6 lg:grid-cols-12 lg:px-8 lg:py-28"
          >
            <Heading
              id="benchmark"
              className="pb-6 text-[clamp(2.25rem,3vw,3rem)] lg:col-span-6 lg:col-start-7 lg:row-start-1 lg:pt-4 lg:pb-8"
            >
              The benchmark
            </Heading>
            <div className="rise flex flex-col justify-between gap-16 bg-runway p-7 text-tarmac lg:col-span-6 lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:min-h-[70vh]">
              <p className="display text-[clamp(3rem,6vw,6rem)]">18 of 20</p>
              <p className="max-w-[34ch] text-lg leading-relaxed">
                real breaks stopped from the code, in 32 scenarios on real git
                checkouts. git merge-tree stops 3, file leases 4. The other two
                get a warning from the flight plans.
              </p>
            </div>
            <div className="grid content-start gap-2 lg:col-span-6 lg:col-start-7 lg:row-start-2 lg:grid-cols-2">
              <div className="rise-2 flex flex-col justify-between gap-12 bg-paint p-7 text-tarmac lg:min-h-[44vh]">
                <p className="display text-[clamp(3rem,6vw,6rem)]">0 of 12</p>
                <p className="text-lg leading-relaxed">
                  safe scenarios stopped. File leases stop 6 of them.
                </p>
              </div>
              <div className="rise-3 flex flex-col justify-between gap-12 bg-raised p-7 lg:mt-24 lg:min-h-[34vh]">
                <p className="display text-[clamp(3rem,6vw,6rem)]">0 of 190</p>
                <p className="text-lg leading-relaxed">
                  clean merged PRs from cognee, ESP-Website and Django stopped.
                  Git conflicted on 4, and Detente stopped all 4.
                </p>
              </div>
              <p className="pt-8 text-lg leading-relaxed lg:col-span-2">
                We wrote the scenarios ourselves, so they show what each tool
                can see, not how often it catches real conflicts. The real
                merges can&apos;t show catches git misses, because breaks like
                that rarely survive in a project&apos;s history. Run{" "}
                {mono("make bench")} and{" "}
                {mono('make bench-real REPOS="<clones>"')} to check.
              </p>
            </div>
          </section>

          <section
            id="switch"
            aria-labelledby="switch-title"
            className="grid scroll-mt-8 gap-10 bg-panel px-4 py-24 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:px-8 lg:py-28"
          >
            <div className="grid content-start gap-6 lg:sticky lg:top-8 lg:col-span-6 lg:self-start">
              <Heading id="switch">Under the hood</Heading>
              <p className="rise-2 text-lg leading-relaxed">
                Detente runs as an agent in your team&apos;s chat, on{" "}
                <a
                  href="https://github.com/sandbox-quantum/switch"
                  className="underline underline-offset-4"
                >
                  Switch
                </a>
                . Without it, agents on different laptops can&apos;t see each
                other and there&apos;s nowhere for a person to decide.
              </p>
              <p className="rise-3 text-lg leading-relaxed">
                The showcase and the real app share the radar and conflict
                screens and nothing else. The showcase plays recorded runs with
                no sign-in and no server; the real app shows your team&apos;s
                live data after sign-in. {mono("make test")} fails if either one
                reaches into the other.
              </p>
            </div>
            <table className="w-full text-left text-lg lg:col-span-6 lg:col-start-7">
              <caption className="pb-4 text-left text-lg font-medium">
                What Detente uses Switch for
              </caption>
              <tbody>
                {SWITCH.map(([feature, use]) => (
                  <tr key={feature} className={`${ROW} align-top`}>
                    <th
                      scope="row"
                      className={`py-4 pr-6 text-[15px] leading-7 font-normal text-runway`}
                    >
                      <code className={CODE_FONT}>{feature}</code>
                    </th>
                    <td className="py-4 leading-relaxed">{use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section
            id="limits"
            aria-labelledby="limits-title"
            className="grid scroll-mt-8 gap-12 px-4 py-24 sm:px-6 lg:grid-cols-12 lg:px-8 lg:py-28"
          >
            <Heading id="limits" className="lg:col-span-12">
              What it can&apos;t do yet
            </Heading>
            <div className="limits rise-2 lg:col-span-8">
              {LIMITS.map((card, index) => (
                <details
                  key={card.topic}
                  name="limit"
                  open={index === 0}
                  className={`limit ${CARD_TONES[index % CARD_TONES.length]}`}
                  style={{ "--step": index } as CSSProperties}
                >
                  <summary>
                    <span className="limit-tab">{card.topic}</span>
                    <span className="limit-question">{card.question}</span>
                  </summary>
                  <ul>
                    {card.items.map((item, line) => (
                      <li key={line}>{item}</li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
            <div className="grid content-start gap-6 lg:col-span-4 lg:col-start-9 lg:self-end">
              <h3 className="display text-3xl">Prior art</h3>
              <p className="max-w-[60ch] text-lg leading-relaxed">
                Tools near this space include MCP Agent Mail, Dibs and Interlock
                (file leases for agents), GitLive, Sturdy and Deconflict
                (pre-push conflict detection for people), and agent coordinators
                such as Clash, Regente, Braidkeep, Shepherd and Wit.
                Detente&apos;s bet is contract collisions between different
                files, on different laptops, decided by a person in team chat.
              </p>
            </div>
          </section>
        </main>

        <footer className="grid gap-14 bg-panel px-4 pt-20 pb-8 sm:px-6 lg:px-8">
          <p aria-label="Detente" className="mark">
            {"DETENTE".split("").map((letter, index) => (
              <span key={index} aria-hidden data-step={index % 4}>
                {letter}
              </span>
            ))}
          </p>
          <div className="grid gap-10 text-base sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
            <nav
              aria-label="Docs"
              className="grid content-start gap-2 lg:col-span-3"
            >
              <h2 className="text-lg font-semibold">On this page</h2>
              {PLACES.map((place) => (
                <a
                  key={place.id}
                  href={`#${place.id}`}
                  className="underline-offset-4 hover:underline"
                >
                  {place.label}
                </a>
              ))}
            </nav>
            <nav
              aria-label="Site"
              className="grid content-start gap-2 lg:col-span-3"
            >
              <h2 className="text-lg font-semibold">The site</h2>
              <Link href="/" className="underline-offset-4 hover:underline">
                Home
              </Link>
              <Link
                href="/showcase"
                className="underline-offset-4 hover:underline"
              >
                Showcase
              </Link>
              <Link
                href="/get-started"
                className="underline-offset-4 hover:underline"
              >
                Set up
              </Link>
            </nav>
            <nav
              aria-label="Code"
              className="grid content-start gap-2 lg:col-span-3"
            >
              <h2 className="text-lg font-semibold">The code</h2>
              <a href={REPO_URL} className="underline-offset-4 hover:underline">
                GitHub
              </a>
              <a
                href="https://pypi.org/project/detente/"
                className="underline-offset-4 hover:underline"
              >
                PyPI
              </a>
              <a
                href={`${REPO_URL}/blob/main/cli/README.md`}
                className="underline-offset-4 hover:underline"
              >
                CLI guide
              </a>
              <a
                href={`${REPO_URL}/blob/main/CHANGELOG.md`}
                className="underline-offset-4 hover:underline"
              >
                Changelog
              </a>
            </nav>
            <div className="grid content-start gap-2 lg:col-span-3">
              <h2 className="text-lg font-semibold">License</h2>
              <p>
                MIT. Runs on your own machines, and sends nothing anywhere else.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-end justify-between gap-6 text-sm leading-relaxed text-dim">
            <p className="max-w-[90ch]">
              Pictures:{" "}
              <a
                href="https://commons.wikimedia.org/wiki/File:Ben_Gurion_International_Airport_4_taxiway_signs.JPG"
                className="underline underline-offset-2"
              >
                Ben Gurion International Airport 4 taxiway signs
              </a>
              , CC0;{" "}
              <a
                href="https://commons.wikimedia.org/wiki/File:SFO_Control_tower,_night._(28125162268).jpg"
                className="underline underline-offset-2"
              >
                SFO Control tower, night
              </a>{" "}
              by mliu92, CC BY-SA 2.0;{" "}
              <a
                href="https://commons.wikimedia.org/wiki/File:Flight_control_strip_at_Jakarta_control.jpg"
                className="underline underline-offset-2"
              >
                Flight control strip at Jakarta control
              </a>
              , public domain. All via Wikimedia Commons.
            </p>
            <a
              href={REPO_URL}
              className="bg-runway px-4 py-2.5 text-base font-medium text-tarmac transition-colors hover:bg-paint"
            >
              Get the code
            </a>
          </div>
        </footer>
      </div>
    </TowerProvider>
  );
}
