import type { ReactNode } from "react";
import { Sign } from "@/components/sign";
import { type Conflict, conflictHeadline, conflictLocation, type SignKind } from "@/lib/radar";

const STATUS: Record<Conflict["status"], { label: string; sign: SignKind }> = {
  open: { label: "Hold", sign: "hold" },
  decided: { label: "Fix under way", sign: "traffic" },
  resolved: { label: "Cleared", sign: "cleared" },
};

type ConflictScreenProps = {
  conflict: Conflict;
  onPick?: (key: string) => void;
  children: ReactNode;
};

export function ConflictScreen({ conflict, onPick, children }: ConflictScreenProps) {
  const location = conflictLocation(conflict);
  const status = STATUS[conflict.status];

  return (
    <article className="grid gap-6 lg:grid-cols-2 lg:gap-x-10">
      <header
        className="field grid gap-3 border-4 border-transparent p-5 sm:p-8 lg:col-span-2"
        data-kind={status.sign}
      >
        <p className="display text-3xl">{status.label}</p>
        <h1 className="font-display text-[clamp(1.75rem,4.4vw,3.75rem)] leading-[1.02] font-bold text-balance">
          {conflictHeadline(conflict)}
        </h1>
        <p>
          Conflict room <code className="font-mono text-sm">{conflict.id}</code>
        </p>
      </header>

      <div className="grid content-start gap-6">
        {conflict.before && conflict.after && (
          <section aria-labelledby="change-title" className="grid gap-3">
            <h2 id="change-title" className="display text-3xl">
              The contract change
            </h2>
            <pre className="overflow-x-auto bg-tarmac p-4 font-mono text-sm leading-7">
              <span className="text-beacon">- {conflict.before}</span>
              {"\n"}
              <span className="text-runway">+ {conflict.after}</span>
            </pre>
            <p className="text-dim">
              {conflict.changed_by} made this change in{" "}
              <code className="font-mono text-sm">{conflict.changed_file}</code>.
            </p>
          </section>
        )}

        <section aria-labelledby="breaks-title" className="grid gap-3">
          <h2 id="breaks-title" className="display text-3xl">
            {conflict.kind === "contract" ? "Who it breaks" : "Where they overlap"}
          </h2>
          {conflict.kind === "contract" ? (
            <p className="text-dim">
              {conflict.caller}&apos;s unpushed work at{" "}
              <code className="font-mono text-sm">{location}</code>:{" "}
              <code className="font-mono text-sm">{conflict.breaks.code}</code>
            </p>
          ) : (
            <p className="text-dim">
              {conflict.changed_by} and {conflict.caller} both have unpushed work in{" "}
              <code className="font-mono text-sm">{location}</code>.
            </p>
          )}
        </section>
      </div>

      <section aria-labelledby="fix-title" className="grid content-start gap-3">
        <h2 id="fix-title" className="display text-3xl">
          The fix
        </h2>
        <ul className="grid gap-2">
          {conflict.options.map((option) => {
            const row = (
              <>
                <span className="display flex size-14 shrink-0 items-center justify-center border-2 border-runway bg-tarmac text-4xl text-runway">
                  {option.key}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-lg font-medium">{option.text}</span>
                  <span className="block text-sm text-dim">{option.agent} edits</span>
                </span>
                {conflict.decision?.option === option.key && (
                  <Sign kind="cleared" className="!border-1 text-[15px]">
                    Chosen by {conflict.decision.by}
                  </Sign>
                )}
              </>
            );
            const rowStyle = "flex w-full items-center gap-4 bg-panel p-3 text-left";
            return (
              <li key={option.key}>
                {onPick ? (
                  <button
                    type="button"
                    onClick={() => onPick(option.key)}
                    className={`${rowStyle} cursor-pointer transition-colors hover:bg-raised active:translate-y-0.5`}
                  >
                    {row}
                  </button>
                ) : (
                  <div className={rowStyle}>{row}</div>
                )}
              </li>
            );
          })}
        </ul>
        {children}
      </section>
    </article>
  );
}
