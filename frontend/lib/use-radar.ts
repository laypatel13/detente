"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { RadarState } from "@/lib/radar";

export type Connection = "connecting" | "live" | "lost";

// The API sends its state on connect, so silence means it's stuck, even with the port open.
const FIRST_STATE_TIMEOUT_MS = 4000;
const RETRY_MS = 3000;

export function useRadar() {
  const [state, setState] = useState<RadarState | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const router = useRouter();

  useEffect(() => {
    let source: EventSource;
    let retry: ReturnType<typeof setTimeout>;
    const timeout = setTimeout(() => setConnection("lost"), FIRST_STATE_TIMEOUT_MS);

    async function goToSignInIfSignedOut() {
      const response = await fetch("/api/auth/me").catch(() => null);
      if (response?.status === 401) {
        router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      }
    }

    function connect() {
      source = new EventSource("/api/radar/stream");
      source.onmessage = (event) => {
        clearTimeout(timeout);
        setState(JSON.parse(event.data));
        setConnection("live");
      };
      source.onerror = () => {
        setConnection("lost");
        // EventSource retries a dropped stream by itself, but gives up on an error reply.
        if (source.readyState === EventSource.CLOSED) {
          void goToSignInIfSignedOut();
          retry = setTimeout(connect, RETRY_MS);
        }
      };
    }

    connect();
    return () => {
      clearTimeout(timeout);
      clearTimeout(retry);
      source.close();
    };
  }, [router]);

  return { state, connection };
}
