"use client";

import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";

const APP_LINKS = [
  { href: "/radar", label: "Radar" },
  { href: "/conflicts", label: "Conflicts" },
];

export function AppHeader() {
  const router = useRouter();

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
    router.replace("/login");
  }

  return (
    <SiteHeader links={APP_LINKS}>
      <Button variant="ghost" onClick={signOut}>
        Sign out
      </Button>
    </SiteHeader>
  );
}
