"use client";

import { Pause, Play } from "lucide-react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { useCallback, useState } from "react";
import { Sign } from "@/components/sign";
import { Plane, PLANE_SIZE, Roger, ROGER_SIZE } from "@/components/sprite";
import { Button } from "@/components/ui/button";
import { type Apron, type ApronAlert, type Stand, layoutField, ROAD, VIEW } from "@/lib/airfield";
import type { RadarState } from "@/lib/radar";
import { STATUS_LABEL, STATUS_SIGN } from "@/lib/radar";

const CENTER = VIEW / 2;
const BAR_LENGTH = 76;
const BAR_DEPTH = 14;
const PLATE_HEIGHT = 22;
const SMALLEST_PLATE = 62;
const BIGGEST_PLANE = 4;
const BIGGEST_PLANE_ON_PHONE = 2;

const BAR_FILL: Record<ApronAlert, string> = {
  clear: "var(--ring-line)",
  traffic: "var(--runway)",
  hold: "var(--hold)",
};

const percent = (value: number) => `${(value / VIEW) * 100}%`;

function taxiway({ ringPoint, bend, gate }: Apron) {
  return `M${ringPoint.x} ${ringPoint.y}Q${bend.x} ${bend.y} ${gate.x} ${gate.y}`;
}

function stopBar({ gate, gateOn }: Apron) {
  const flat = gateOn === "top" || gateOn === "bottom";
  const width = flat ? BAR_LENGTH : BAR_DEPTH;
  const height = flat ? BAR_DEPTH : BAR_LENGTH;
  return { x: gate.x - width / 2, y: gate.y - height / 2, width, height };
}

function useWidth() {
  const [width, setWidth] = useState(640);

  // A ref callback measures before first paint, so phones never flash desktop sprites.
  const ref = useCallback((node: HTMLDivElement) => {
    setWidth(node.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return { ref, width };
}

function ApronFloor({ apron }: { apron: Apron }) {
  const box = { x: apron.x, y: apron.y, width: apron.width, height: apron.height };
  return (
    <>
      <motion.rect initial={false} animate={box} transition={{ duration: 0.4 }} fill="var(--panel)" />
      <motion.rect
        initial={false}
        animate={box}
        transition={{ duration: 0.4 }}
        fill={apron.alert === "traffic" ? "var(--runway)" : "var(--hold)"}
        className="transition-opacity duration-500"
        opacity={apron.alert === "hold" ? 0.34 : apron.alert === "traffic" ? 0.12 : 0}
      />
    </>
  );
}

type ParkedPlaneProps = {
  stand: Stand;
  fit: number;
  scale: number;
  plate: string | null;
};

function ParkedPlane({ stand, fit, scale, plate }: ParkedPlaneProps) {
  const { flight, apron, x, y, flip } = stand;
  const place = { left: percent(x), top: percent(y) };
  // Worked out once, so a plane taxis in when it arrives and not on every resize.
  const [taxiIn] = useState(() => ({
    x: [(apron.ringPoint.x - x) * fit, (apron.gate.x - x) * fit, 0],
    y: [(apron.ringPoint.y - y) * fit, (apron.gate.y - y) * fit, 0],
  }));

  return (
    <motion.div
      className="absolute"
      style={{ x: "-50%", y: "-50%" }}
      initial={{ ...place, opacity: 0 }}
      animate={{ ...place, opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.25 } }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        animate={taxiIn}
        transition={{ duration: 1.3, ease: "easeInOut" }}
        className="flex flex-col items-center gap-1"
      >
        <div className={flip ? "-scale-x-100" : undefined}>
          <div className={flight.status === "landed" ? "opacity-50" : undefined}>
            <Plane
              owner={flight.owner}
              status={flight.status}
              scale={scale}
              label={`${flight.callsign}, ${STATUS_LABEL[flight.status]}`}
            />
          </div>
        </div>
        {plate && (
          <div className="flex justify-center" style={{ maxWidth: stand.width * fit - 4 }}>
            <Sign
              kind={STATUS_SIGN[flight.status]}
              className={`!border-1 max-w-full !normal-case ${plate}`}
            >
              <span className="truncate">{flight.callsign}</span>
            </Sign>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

type RadarScopeProps = {
  state: RadarState | null;
  // A parent that runs its own loop, like the landing hero, owns the pause so it can stop the loop too.
  paused?: boolean;
  onPausedChange?: (paused: boolean) => void;
};

export function RadarScope({ state, paused: pausedByParent, onPausedChange }: RadarScopeProps) {
  const { ref, width } = useWidth();
  const [pausedHere, setPausedHere] = useState(false);
  const paused = pausedByParent ?? pausedHere;
  const setPaused = onPausedChange ?? setPausedHere;

  const { ringRadius, aprons, stands, routes } = layoutField(
    state?.flights ?? [],
    state?.links ?? [],
  );
  const mood = state?.mood ?? "resting";
  const fit = width / VIEW;

  const tightest = {
    width: Math.min(...stands.map((stand) => stand.width)) * fit,
    height: Math.min(...stands.map((stand) => stand.height)) * fit,
  };
  const plates =
    tightest.width >= SMALLEST_PLATE && tightest.height >= PLANE_SIZE.height + PLATE_HEIGHT;
  const planeScale = Math.max(
    1,
    Math.min(
      width >= 480 ? BIGGEST_PLANE : BIGGEST_PLANE_ON_PHONE,
      Math.floor(
        Math.min(
          (tightest.width * 0.9) / PLANE_SIZE.width,
          (tightest.height - (plates ? PLATE_HEIGHT : 0)) / PLANE_SIZE.height,
        ),
      ),
    ),
  );
  const rogerScale = Math.max(
    1,
    Math.floor(((ringRadius * 2 - ROAD) * fit) / ROGER_SIZE.height),
  );
  const plateSize = width >= 480 ? "text-[15px]" : "text-[13px]";

  return (
    <MotionConfig reducedMotion="user">
      <div
        data-ui
        ref={ref}
        data-paused={paused}
        className="relative aspect-square w-full overflow-hidden"
      >
        <svg
          viewBox={`0 0 ${VIEW} ${VIEW}`}
          className="absolute inset-0 size-full"
          role="img"
          aria-label={`Radar. ${state?.headline ?? "Waiting for Detente."}`}
        >
          <rect width={VIEW} height={VIEW} fill="var(--tarmac)" />

          {aprons.map((apron) => (
            <ApronFloor key={apron.name} apron={apron} />
          ))}

          <g key={aprons.length} fill="none" stroke="var(--raised)" strokeWidth={ROAD}>
            {aprons.map((apron) => (
              <path key={apron.name} d={taxiway(apron)} />
            ))}
            <circle cx={CENTER} cy={CENTER} r={ringRadius} fill="var(--sky)" />
          </g>

          <g
            key={`lines-${aprons.length}`}
            fill="none"
            stroke="var(--runway)"
            strokeWidth="4"
            strokeDasharray="14 14"
          >
            {aprons.map((apron) => (
              // Lights run out to a plane that's free to go, and stop for one that's held.
              <path
                key={apron.name}
                d={taxiway(apron)}
                className={apron.alert === "hold" ? undefined : "taxi-lights"}
              />
            ))}
            <circle cx={CENTER} cy={CENTER} r={ringRadius} />
          </g>

          {aprons.map((apron) => (
            <rect
              key={apron.name}
              {...stopBar(apron)}
              fill={BAR_FILL[apron.alert]}
              className={apron.alert === "hold" ? "alarm" : undefined}
            />
          ))}

          {routes.map((route) =>
            route.kind === "collision" ? (
              <motion.path
                key={route.key}
                d={route.path}
                className="alarm"
                fill="none"
                stroke="var(--beacon)"
                strokeWidth="8"
                strokeLinejoin="round"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            ) : (
              <motion.path
                key={route.key}
                d={route.path}
                fill="none"
                stroke="var(--runway)"
                strokeWidth="6"
                strokeDasharray="12 14"
                strokeLinecap="round"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              />
            ),
          )}
        </svg>

        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <motion.div
            key={mood}
            initial={{ scale: mood === "collision" ? 1.18 : 1.05 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 420, damping: 16 }}
          >
            <Roger mood={mood} scale={rogerScale} />
          </motion.div>
        </div>

        {aprons.map((apron) => (
          <motion.div
            key={apron.name}
            className="absolute"
            initial={false}
            animate={{ left: percent(apron.x + 6), top: percent(apron.y + 6) }}
            transition={{ duration: 0.4 }}
          >
            <Sign kind="traffic" className={`!border-1 !normal-case ${plateSize}`}>
              {apron.name}/
            </Sign>
          </motion.div>
        ))}

        <AnimatePresence initial={false}>
          {stands.map((stand) => (
            <ParkedPlane
              key={stand.flight.callsign}
              stand={stand}
              fit={fit}
              scale={planeScale}
              plate={plates ? plateSize : null}
            />
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {routes
            .filter((route) => route.kind === "collision")
            .map((route) => (
              <motion.div
                key={route.key}
                className="absolute"
                style={{
                  left: percent(route.mark.x),
                  top: percent(route.mark.y),
                  x: "-50%",
                  y: "-50%",
                }}
                initial={{ scale: 2.2, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 18 }}
              >
                <Sign kind="hold" className="text-lg sm:text-2xl">
                  Hold
                </Sign>
              </motion.div>
            ))}
        </AnimatePresence>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-0 bottom-0 text-dim"
          aria-label={paused ? "Play the radar" : "Pause the radar"}
          title={paused ? "Play the radar" : "Pause the radar"}
          onClick={() => setPaused(!paused)}
        >
          {paused ? <Play aria-hidden /> : <Pause aria-hidden />}
        </Button>
      </div>
    </MotionConfig>
  );
}
