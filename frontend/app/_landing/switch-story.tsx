"use client";

import { useEffect, useRef, useState } from "react";
import { SwitchFeed } from "@/components/switch-feed";
import type { FeedMessage } from "@/lib/radar";
import { cn } from "@/lib/utils";
import { COLLISION, DECIDED, DECISION, FLIGHT_PLAN, RESOLVED, TRAFFIC } from "./messages";

type Part = {
  title: string;
  text: string;
  uses: string[];
  rooms: { name: string; open: boolean }[];
  members: string[];
  feed: FeedMessage[];
};

const TOWER = "tower";
const CONFLICT = "conflict-create-session-3f1a";
const EVERYONE = ["Detente", "lay", "developer-a", "developer-b", "Wilco", "Mayday", "Squawk"];

const PARTS: Part[] = [
  {
    title: "One room, every laptop",
    text: "Every agent joins the tower room through Switch, wherever it's running. This is the only reason agents on different machines can see each other at all.",
    uses: ["rooms", "agent protocol", "room instructions"],
    rooms: [{ name: TOWER, open: true }],
    members: EVERYONE,
    feed: [FLIGHT_PLAN, TRAFFIC],
  },
  {
    title: "A collision gets its own room",
    text: "Detente opens a conflict room with both people and both agents, links it to the tower room, and addresses the decision to exactly who's involved.",
    uses: ["create_room", "link_rooms", "send_targeted_message"],
    rooms: [
      { name: TOWER, open: false },
      { name: CONFLICT, open: true },
    ],
    members: ["Detente", "lay", "developer-a", "Wilco", "Mayday"],
    feed: [COLLISION, DECISION],
  },
  {
    title: "The room cleans up after itself",
    text: "Once a person has picked and the code fits again, Detente archives the conflict room and lifts the holds.",
    uses: ["archive_room", "room documents"],
    rooms: [{ name: TOWER, open: true }],
    members: EVERYONE,
    feed: [DECIDED, RESOLVED],
  },
  {
    title: "One controller, even after a crash",
    text: "Detente holds Switch's exclusive tower role, so there's only ever one controller. If it goes down, it reads back what it missed and the holds survive.",
    uses: ["exclusive role", "read_context"],
    rooms: [{ name: TOWER, open: true }],
    members: EVERYONE,
    feed: [TRAFFIC, COLLISION],
  },
];

function RoomWindow({ part, tall = false }: { part: Part; tall?: boolean }) {
  return (
    <div
      data-ui
      className={cn(
        "grid gap-3 bg-panel p-4 text-ink sm:grid-cols-[12rem_minmax(0,1fr)]",
        tall && "min-h-[62svh]",
      )}
    >
      <div className="grid content-start gap-5 text-[15px]">
        <div className="grid gap-1">
          <p className="font-display text-lg font-semibold">Rooms</p>
          <ul className="grid gap-1">
            {part.rooms.map((room) => (
              <li
                key={room.name}
                title={room.name}
                className={cn("truncate px-2 py-1", room.open ? "bg-raised font-medium" : "text-dim")}
              >
                {room.name}
              </li>
            ))}
          </ul>
        </div>
        <div className="hidden gap-1 sm:grid">
          <p className="font-display text-lg font-semibold">In this room</p>
          <ul className="grid gap-1 px-2">
            {part.members.map((member) => (
              <li key={member}>{member}</li>
            ))}
          </ul>
        </div>
      </div>
      {/* Newest messages sit at the bottom, as in any chat. */}
      <div className={cn("flex min-w-0 flex-col bg-sky p-4", tall && "justify-end [&>ol]:flex-none")}>
        <SwitchFeed feed={part.feed} />
      </div>
    </div>
  );
}

export function SwitchStory() {
  const [active, setActive] = useState(0);
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    const items = [...(list.current?.children ?? [])];
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(items.indexOf(entry.target));
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    items.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="mt-10 grid gap-12 lg:grid-cols-[7fr_5fr]">
      <div className="hidden self-start lg:sticky lg:top-[19svh] lg:block">
        <div key={active} className="animate-in fade-in duration-200">
          <RoomWindow part={PARTS[active]} tall />
        </div>
      </div>

      <ol ref={list} className="grid gap-16 lg:gap-0">
        {PARTS.map((part, index) => (
          // On desktop the step the window shows is the one in full ink.
          <li
            key={part.title}
            data-active={index === active}
            className="grid content-center gap-4 transition-opacity duration-300 lg:min-h-[58svh] lg:data-[active=false]:opacity-35"
          >
            <h3 className="rise display text-[clamp(2rem,3.2vw,3rem)]">{part.title}</h3>
            <p className="rise-2 text-lg leading-relaxed">{part.text}</p>
            <p className="rise-2 flex flex-wrap gap-2">
              {part.uses.map((use) => (
                <code key={use} className="bg-tarmac px-2 py-1 font-mono text-sm text-runway">
                  {use}
                </code>
              ))}
            </p>
            <div className="lg:hidden">
              <RoomWindow part={part} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
