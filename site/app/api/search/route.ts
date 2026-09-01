import { NextRequest } from "next/server";
import { searchDocs } from "@/lib/content";

export function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  return Response.json({
    query,
    results: searchDocs(query)
  });
}
