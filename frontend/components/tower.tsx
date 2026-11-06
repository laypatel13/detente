import Link from "next/link";
import { connection } from "next/server";
import { type ReactNode, Suspense } from "react";

export const REPO_URL = "https://github.com/laypatel13/detente";

/**
 * Whether a tower stands behind this copy of the site. The copy a team runs is started with the
 * API's address; the hosted copy, which only shows the public pages, isn't. Read on each request,
 * because the Docker image is built once and given the address when it starts.
 */
async function hasTower() {
  await connection();
  return Boolean(process.env.DETENTE_API_URL);
}

async function Choose({ yes, no }: { yes: ReactNode; no: ReactNode }) {
  return (await hasTower()) ? yes : no;
}

/** `children` when a tower stands behind the site, `otherwise` when it doesn't. */
export function IfTower({ children, otherwise = null }: { children: ReactNode; otherwise?: ReactNode }) {
  return (
    <Suspense fallback={null}>
      <Choose yes={children} no={otherwise} />
    </Suspense>
  );
}

const ACTION = "hidden text-lg font-medium underline-offset-4 hover:underline focus-visible:underline sm:inline";

/** The header's one action: signing in where there's a radar to sign in to, the code where there isn't. */
export function TowerAction() {
  return (
    <IfTower
      otherwise={
        <a href={REPO_URL} className={ACTION}>
          GitHub
        </a>
      }
    >
      <Link href="/login" className={ACTION}>
        Sign in
      </Link>
    </IfTower>
  );
}
