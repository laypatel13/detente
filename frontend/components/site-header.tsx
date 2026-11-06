import Link from "next/link";
import type { ReactNode } from "react";
import { RogerBadge } from "@/components/sprite";

export type NavLink = { href: string; label: string };

export const PUBLIC_LINKS: NavLink[] = [
  { href: "/showcase", label: "Showcase" },
  { href: "/get-started", label: "Set up" },
  { href: "/docs", label: "Docs" },
];

type SiteHeaderProps = { links: NavLink[]; note?: ReactNode; children?: ReactNode };

export function SiteHeader({ links, note, children }: SiteHeaderProps) {
  return (
    <header className="flex min-h-16 shrink-0 flex-wrap items-center gap-x-5 gap-y-2 px-4 py-2 sm:px-6 lg:px-8">
      <Link href="/" className="flex items-center gap-2" aria-label="Detente home">
        <RogerBadge mood="watching" scale={2} />
        <span className="display text-3xl">Detente</span>
      </Link>
      <nav aria-label="Main" className="flex items-center gap-5 text-lg font-medium">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="underline-offset-4 hover:underline focus-visible:underline"
          >
            {link.label}
          </Link>
        ))}
      </nav>
      {note && <div className="order-last basis-full lg:order-none lg:basis-auto">{note}</div>}
      <div className="ml-auto flex items-center gap-3">{children}</div>
    </header>
  );
}
