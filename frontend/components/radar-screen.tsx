import Link from "next/link";
import type { ReactNode } from "react";
import { FlightStrip } from "@/components/flight-strip";
import { RadarScope } from "@/components/radar-scope";
import { RadioLine } from "@/components/radio-line";
import { Sign } from "@/components/sign";
import { Plane } from "@/components/sprite";
import { SwitchFeed } from "@/components/switch-feed";
import { type RadarState, STATUS_LABEL, STATUS_SIGN } from "@/lib/radar";
import { cn } from "@/lib/utils";

type RadarScreenProps = {
  title: string;
  state: RadarState | null;
  conflictHref: (id: string) => string;
  guide?: ReactNode;
};

// Draws whatever state it's given. It has no idea where that state came from.
export function RadarScreen({ title, state, conflictHref, guide }: RadarScreenProps) {
  const openConflict = state?.conflicts.find((conflict) => conflict.status === "open");

  return (
    <main className="mx-auto grid w-full max-w-[1640px] flex-1 gap-x-6 gap-y-4 px-4 pb-4 sm:px-6 lg:h-[calc(100dvh-4rem)] lg:flex-none lg:grid-cols-[minmax(0,1fr)_minmax(400px,36%)] lg:grid-rows-[minmax(0,1fr)]">
      <h1 className="sr-only">{title}</h1>

      <section aria-label="Radar" className="flex min-h-0 min-w-0 flex-col gap-3">
        {!guide && (
          <div className="flex min-h-12 items-center justify-between gap-4">
            {state && <RadioLine state={state} />}
            {openConflict && (
              <Link
                href={conflictHref(openConflict.id)}
                className="shrink-0 font-medium text-beacon underline underline-offset-4"
              >
                See what broke
              </Link>
            )}
          </div>
        )}

        <div className="scope-room">
          <div>
            <RadarScope state={state} />
          </div>
        </div>

        <ul
          className={cn(
            "max-h-28 gap-x-6 gap-y-2 overflow-y-auto sm:grid-cols-3",
            guide ? "hidden lg:grid" : "grid",
          )}
        >
          {state?.crew.map((member) => {
            const flight = state.flights.find((item) => item.callsign === member.callsign);
            const status = flight?.status ?? "parked";
            return (
              <li key={member.callsign} className="flex min-w-0 items-center gap-3">
                <Plane
                  owner={member.owner}
                  status={status === "parked" ? "cleared" : status}
                  scale={2}
                  label=""
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{member.person}</span>
                    <Sign kind={STATUS_SIGN[status]} className="!border-1 text-sm">
                      {STATUS_LABEL[status]}
                    </Sign>
                  </div>
                  <div className="truncate text-sm text-dim">on {member.vendor}</div>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <aside className="flex min-h-0 min-w-0 flex-col gap-4">
        {guide}

        <section aria-labelledby="strips-title">
          <h2 id="strips-title" className="mb-2 font-display text-xl font-semibold">
            Flight strips
          </h2>
          {state?.flights.length ? (
            <ul className="space-y-1">
              {state.flights.map((flight) => (
                <FlightStrip key={flight.callsign} flight={flight} />
              ))}
            </ul>
          ) : (
            <p className="text-dim">
              No flights yet. A strip appears when an agent files a flight plan.
            </p>
          )}
        </section>

        <section aria-labelledby="feed-title" className="flex h-96 flex-1 flex-col lg:h-auto lg:min-h-0">
          <h2 id="feed-title" className="mb-2 font-display text-xl font-semibold">
            Switch feed
          </h2>
          <SwitchFeed feed={state?.feed ?? []} />
        </section>
      </aside>
    </main>
  );
}
