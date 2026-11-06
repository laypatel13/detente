import { type NextRequest, NextResponse } from "next/server";

// A quick first check, so nobody sees an empty app. The API is what really refuses access.
export function proxy(request: NextRequest) {
  if (!process.env.DETENTE_API_URL) {
    // No tower behind this copy of the site, so there's no radar to sign in to. Say where it runs.
    return NextResponse.rewrite(new URL("/no-tower", request.url));
  }
  const { pathname } = request.nextUrl;
  if (pathname !== "/login" && !request.cookies.has("detente_session")) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/radar", "/conflicts", "/conflicts/:path*", "/login"],
};
