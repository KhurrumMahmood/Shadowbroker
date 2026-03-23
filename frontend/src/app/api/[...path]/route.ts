/**
 * Catch-all proxy route — forwards /api/* requests from the browser to the
 * backend server. BACKEND_URL is a plain server-side env var (not NEXT_PUBLIC_),
 * so it is read at request time from the runtime environment, never baked into
 * the client bundle or the build manifest.
 *
 * Set BACKEND_URL in docker-compose `environment:` (e.g. http://backend:8000)
 * to use Docker internal networking. Defaults to http://localhost:8000 for
 * local development where both services run on the same host.
 */

import { NextRequest, NextResponse } from "next/server";

// Headers that must not be forwarded to the backend.
const STRIP_REQUEST = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailers", "transfer-encoding", "upgrade", "host",
]);

// Headers that must not be forwarded back to the browser.
// content-encoding and content-length are stripped because Node.js fetch()
// automatically decompresses gzip/br responses — forwarding the compressed
// content-length would cause browsers to truncate the decompressed body.
const STRIP_RESPONSE = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailers", "transfer-encoding", "upgrade",
  "content-encoding", "content-length",
]);

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const targetUrl = new URL(`/api/${path.join("/")}`, backendUrl);
  targetUrl.search = req.nextUrl.search;

  // Forward relevant request headers
  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!STRIP_REQUEST.has(key.toLowerCase())) {
      forwardHeaders.set(key, value);
    }
  });

  const isBodyless = req.method === "GET" || req.method === "HEAD";

  // For GET requests, buffer the response and retry once on socket errors.
  // Railway's internal networking can drop sockets mid-stream on large responses
  // (e.g. the 11MB /api/live-data/fast payload), causing "other side closed" errors
  // when streaming. Buffering + retry eliminates these intermittent failures.
  if (isBodyless) {
    const maxAttempts = 2;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const upstream = await fetch(targetUrl.toString(), {
          method: req.method,
          headers: forwardHeaders,
          signal: AbortSignal.timeout(30_000),
        });

        if (upstream.status === 304) {
          const h = new Headers();
          upstream.headers.forEach((v, k) => { if (!STRIP_RESPONSE.has(k.toLowerCase())) h.set(k, v); });
          return new NextResponse(null, { status: 304, headers: h });
        }

        // Buffer the full body so a mid-stream socket close is caught here (and retried)
        const body = await upstream.arrayBuffer();

        const responseHeaders = new Headers();
        upstream.headers.forEach((v, k) => { if (!STRIP_RESPONSE.has(k.toLowerCase())) responseHeaders.set(k, v); });
        responseHeaders.set("content-length", String(body.byteLength));

        return new NextResponse(body, { status: upstream.status, headers: responseHeaders });
      } catch (err) {
        if (attempt < maxAttempts) continue; // retry once
        return new NextResponse(JSON.stringify({ error: "Backend unavailable" }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
  }

  // POST/PUT/DELETE — stream without retry (request bodies can't be replayed)
  let upstream: Response;
  try {
    upstream = await fetch(targetUrl.toString(), {
      method: req.method,
      headers: forwardHeaders,
      body: req.body,
      // @ts-ignore
      duplex: "half",
      signal: AbortSignal.timeout(30_000),
    });
  } catch (err) {
    return new NextResponse(JSON.stringify({ error: "Backend unavailable" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIP_RESPONSE.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  if (upstream.status === 304) {
    return new NextResponse(null, { status: 304, headers: responseHeaders });
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
