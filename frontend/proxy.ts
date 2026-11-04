import { type NextRequest, NextResponse } from "next/server";

// A quick first check, so nobody sees an empty app. The API is what really refuses access.
export function proxy(request: NextRequest) {
  if (!process.env.DETENTE_API_URL) {
    return NextResponse.redirect(new URL("/get-started", request.url));
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
