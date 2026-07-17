import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const proxyRoot = (process.env.AGENTWARDEN_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "");

export async function GET() {
  const response = await fetch(`${proxyRoot}/config`, { cache: "no-store" });
  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}

export async function PUT(request: NextRequest) {
  const payload = await request.json();
  const response = await fetch(`${proxyRoot}/config`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const result = await response.json();
  return NextResponse.json(result, { status: response.status });
}
