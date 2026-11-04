"use client";

import DecryptedText from "@/components/DecryptedText";
import { Sign } from "@/components/sign";
import { RogerBadge } from "@/components/sprite";
import { FACE, MOOD_SIGN, type RadarState } from "@/lib/radar";

// Roger's current radio call. The landing page decodes each new call as it arrives.
export function RadioLine({ state, decode = false }: { state: RadarState; decode?: boolean }) {
  return (
    <div role="status" className="flex min-w-0 items-center gap-3">
      <RogerBadge mood={state.mood} scale={2} />
      <Sign kind={MOOD_SIGN[state.mood]} className="!border-1 text-[15px]">
        {FACE[state.mood]}
      </Sign>
      <p className="min-w-0 leading-snug font-medium">
        {decode ? (
          <DecryptedText
            key={state.headline}
            text={state.headline}
            animateOn="view"
            sequential
            speed={14}
            encryptedClassName="text-dim"
          />
        ) : (
          state.headline
        )}
      </p>
    </div>
  );
}
