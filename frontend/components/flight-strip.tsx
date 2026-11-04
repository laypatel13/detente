import { Sign } from "@/components/sign";
import { Plane } from "@/components/sprite";
import { type Flight, STATUS_LABEL, STATUS_SIGN } from "@/lib/radar";

// Modeled on the paper strips controllers keep in a rack, one per aircraft.
export function FlightStrip({ flight }: { flight: Flight }) {
  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 bg-panel px-3 py-2">
      <div className={flight.status === "landed" ? "opacity-50" : undefined}>
        <Plane owner={flight.owner} status={flight.status} scale={2} label="" />
      </div>
      <div className="min-w-0">
        <code className="block truncate font-mono text-sm font-medium">{flight.callsign}</code>
        <p className="truncate text-sm text-dim">
          {flight.task}, <code className="font-mono text-[13px]">{flight.files.join(", ")}</code>
        </p>
      </div>
      <Sign kind={STATUS_SIGN[flight.status]} className="!border-1 text-[15px]">
        {STATUS_LABEL[flight.status]}
      </Sign>
    </li>
  );
}
