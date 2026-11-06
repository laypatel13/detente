"use client";

import Image from "next/image";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useId,
  useState,
  useSyncExternalStore,
} from "react";

// The docs' one live thing: type your tower's address once, and every command and link on the
// page uses it. Without script, everything reads localhost, which is right on the tower machine.

const DEFAULT = "localhost";
const KEY = "detente-docs-tower";
const Tower = createContext<{ host: string; setHost: (host: string) => void }>({
  host: DEFAULT,
  setHost: () => {},
});

/** Takes what people paste (a URL, a host with a port) and keeps only the host. */
function hostOf(text: string) {
  const host = text
    .trim()
    .replace(/^[a-z]+:\/\//i, "")
    .replace(/[/?#].*$/, "")
    .replace(/:\d+$/, "");
  return host || DEFAULT;
}

// The address lives in this browser's storage, so it's still there on the next visit. When storage
// is blocked it lives in memory for the visit instead.
let memory = DEFAULT;
const listeners = new Set<() => void>();
function read() {
  try {
    return localStorage.getItem(KEY) || memory;
  } catch {
    return memory;
  }
}
function write(host: string) {
  memory = host;
  try {
    localStorage.setItem(KEY, host);
  } catch {}
  listeners.forEach((listener) => listener());
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function TowerProvider({ children }: { children: ReactNode }) {
  const host = useSyncExternalStore(subscribe, read, () => DEFAULT);
  return (
    <Tower.Provider value={{ host, setHost: write }}>{children}</Tower.Provider>
  );
}

const fill = (text: string, host: string) => text.replaceAll("{tower}", host);

/** Commands, hosts and URLs are literal code, so they keep the code face. */
export const CODE_FONT = "font-mono"; // taste-skill-ignore: literal commands, hosts and URLs

export function TowerField() {
  const { host, setHost } = useContext(Tower);
  // What's typed, or the address remembered from a visit before.
  const [typed, setTyped] = useState<string | null>(null);
  const text = typed ?? (host === DEFAULT ? "" : host);
  const id = useId();
  return (
    <div className="grid gap-2">
      <label htmlFor={id} className="text-lg font-medium">
        Your tower&apos;s address
      </label>
      <input
        id={id}
        value={text}
        placeholder={DEFAULT}
        inputMode="url"
        autoComplete="off"
        spellCheck={false}
        aria-describedby={`${id}-note`}
        onChange={(event) => {
          setTyped(event.target.value);
          setHost(hostOf(event.target.value));
        }}
        className={`h-14 w-full max-w-md bg-tarmac px-4 ${CODE_FONT} text-lg text-runway placeholder:text-dim focus-visible:outline-offset-0`}
      />
      <p id={`${id}-note`} className="max-w-[48ch] text-base leading-relaxed">
        <code className={CODE_FONT}>localhost</code> on the tower machine, or
        its <code className={CODE_FONT}>TOWER_ADDR</code> from any other laptop.
        Every command and link below uses it.
      </p>
    </div>
  );
}

/** A tower address, live. `{tower}` in `href` and `text` becomes the address typed above. */
export function TowerLink({ href, text }: { href: string; text?: string }) {
  const { host } = useContext(Tower);
  const url = fill(href, host);
  return (
    <a href={url} className="underline underline-offset-4 hover:text-runway">
      <code className={`${CODE_FONT} [overflow-wrap:anywhere]`}>
        {fill(text ?? href, host)}
      </code>
    </a>
  );
}

/** A block of commands to copy. `{tower}` becomes the address typed above. */
export function Code({ children }: { children: string }) {
  const { host } = useContext(Tower);
  const text = fill(children, host);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(timer);
  }, [copied]);
  return (
    <div className="relative">
      <pre
        className={`overflow-x-auto bg-tarmac p-4 pr-24 ${CODE_FONT} text-[15px] leading-7 text-paint`}
      >
        {text}
      </pre>
      <button
        type="button"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
          } catch {}
        }}
        className="absolute top-2 right-2 min-h-10 bg-raised px-3 text-base font-medium transition-[background-color,transform] hover:bg-runway hover:text-tarmac active:scale-95"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

export type Shelf = {
  name: string;
  picture?: string;
  rows: { cmd: string; does: ReactNode }[];
  note?: ReactNode;
};

type Picture = { src: string; width: number; height: number; alt: string };

/**
 * Every command, as bars that open in place. The terminal picture beside them changes to the
 * group you open, with a slow crossfade.
 */
export function CommandShelf({
  shelves,
  pictures,
}: {
  shelves: Shelf[];
  pictures: Record<string, Picture>;
}) {
  const first =
    shelves.find((shelf) => shelf.picture)?.picture ?? Object.keys(pictures)[0];
  const [shown, setShown] = useState(first);
  return (
    <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
      <div className="grid content-start gap-1.5 lg:col-span-7">
        {shelves.map((shelf, index) => (
          <details
            key={shelf.name}
            name="commands"
            open={index === 0}
            onToggle={(event) => {
              if (event.currentTarget.open && shelf.picture)
                setShown(shelf.picture);
            }}
            className="group bg-raised"
          >
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 text-lg font-medium transition-colors hover:bg-[var(--line)] [&::-webkit-details-marker]:hidden">
              {shelf.name}
              <span
                aria-hidden
                className="text-lg font-bold text-runway transition-transform group-open:rotate-45"
              >
                +
              </span>
            </summary>
            <dl className="grid gap-x-6 gap-y-3.5 px-5 pt-2 pb-6 md:grid-cols-[minmax(0,15rem)_1fr]">
              {shelf.rows.map((row) => (
                <div key={row.cmd} className="contents">
                  <dt className="text-[15px] leading-7 break-words text-runway">
                    <code className={CODE_FONT}>{row.cmd}</code>
                  </dt>
                  <dd className="text-base leading-relaxed">{row.does}</dd>
                </div>
              ))}
              {shelf.note && (
                <p className="text-base leading-relaxed md:col-span-2">
                  {shelf.note}
                </p>
              )}
            </dl>
          </details>
        ))}
      </div>
      <div className="relative hidden lg:col-span-5 lg:block">
        <div className="sticky top-8 grid">
          {Object.entries(pictures).map(([key, picture]) => (
            <Image
              key={key}
              src={picture.src}
              alt={picture.alt}
              width={picture.width}
              height={picture.height}
              sizes="40vw"
              aria-hidden={key !== shown}
              className="crossfade col-start-1 row-start-1 h-auto w-full"
              data-shown={key === shown}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
