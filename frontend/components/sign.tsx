import type { ReactNode } from "react";
import type { SignKind } from "@/lib/radar";
import { cn } from "@/lib/utils";

export function Sign({
  kind,
  className,
  children,
}: {
  kind: SignKind;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span className={cn("sign", className)} data-kind={kind}>
      {children}
    </span>
  );
}
