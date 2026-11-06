/** The arrow on a yellow direction sign. */
export function SignArrow({ flip = false }: { flip?: boolean }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={`size-[1em] shrink-0 ${flip ? "-scale-x-100" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="7"
      aria-hidden
    >
      <path d="M4 24h38M26 8l16 16-16 16" />
    </svg>
  );
}
