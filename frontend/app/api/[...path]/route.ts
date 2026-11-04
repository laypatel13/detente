import type { NextRequest } from "next/server";

// The browser only talks to this app, so the sign-in cookie never crosses origins.
// Laptops call /squawk and /clearance on the API directly, so those stay out of this list.
const OPEN_TO_BROWSERS = ["auth", "radar"];
const REQUEST_HEADERS = ["content-type", "cookie", "x-forwarded-proto"];
const RESPONSE_HEADERS = ["content-type", "cache-control", "x-accel-buffering"];

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: Context) {
  const { path } = await params;
  const api = process.env.DETENTE_API_URL;
  if (!api) return Response.json({ detail: "No Detente server here" }, { status: 503 });
  if (!OPEN_TO_BROWSERS.includes(path[0]) || path.includes("..")) {
    return Response.json({}, { status: 404 });
  }

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const upstream = await fetch(`${api}/${path.map(encodeURIComponent).join("/")}`, {
      method: request.method,
      headers,
      body: request.method === "POST" ? await request.text() : undefined,
      signal: request.signal,
      cache: "no-store",
    });
    const reply = new Headers();
    for (const name of RESPONSE_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) reply.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) reply.append("set-cookie", cookie);
    return new Response(upstream.body, { status: upstream.status, headers: reply });
  } catch {
    return Response.json({ detail: "Detente's API isn't answering" }, { status: 502 });
  }
}

export { forward as GET, forward as POST };
