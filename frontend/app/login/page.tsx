import type { Metadata } from "next";
import { PUBLIC_LINKS, SiteHeader } from "@/components/site-header";
import { SignInForm } from "@/components/sign-in-form";
import { Roger } from "@/components/sprite";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader links={PUBLIC_LINKS} />
      <main className="mx-auto grid w-full max-w-sm flex-1 content-center gap-6 px-4 pb-16">
        <Roger mood="watching" scale={5} />
        <h1 className="display text-5xl">Sign in to your radar</h1>
        <SignInForm />
        <p className="leading-relaxed">
          No account yet? Accounts are made on the tower machine: run{" "}
          <code className="font-mono">make user NAME=yourname</code> there.
        </p>
      </main>
    </div>
  );
}
