"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";

function nextPage() {
  const next = new URLSearchParams(window.location.search).get("next") ?? "/radar";
  // Only ever go somewhere on this site, whatever the link said.
  const target = new URL(next, window.location.origin);
  return target.origin === window.location.origin ? target.pathname : "/radar";
}

async function errorFrom(response: Response | null) {
  if (!response || response.status >= 500) return "Detente isn't answering. Try again soon.";
  if (response.status === 422) return "Wrong username or password";
  const body = await response.json().catch(() => null);
  return body?.detail ?? "Wrong username or password";
}

const FIELD =
  "h-11 w-full rounded-[var(--radius)] border bg-panel px-3 text-base outline-none focus-visible:border-runway";

export function SignInForm() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
    }).catch(() => null);

    if (response?.ok) {
      router.replace(nextPage());
      return;
    }
    setError(await errorFrom(response));
    setPending(false);
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <div className="grid gap-1.5">
        <label htmlFor="username" className="font-medium">
          Username
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          required
          className={FIELD}
        />
      </div>
      <div className="grid gap-1.5">
        <label htmlFor="password" className="font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          aria-describedby={error ? "sign-in-error" : undefined}
          className={FIELD}
        />
        {error && (
          <p id="sign-in-error" role="alert" className="text-sm text-beacon">
            {error}
          </p>
        )}
      </div>
      <Button type="submit" size="lg" disabled={pending} aria-busy={pending}>
        {pending ? "Signing in" : "Sign in"}
      </Button>
    </form>
  );
}
