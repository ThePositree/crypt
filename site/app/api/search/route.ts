import { searchDocuments } from "@/lib/content";

export function GET(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.get("q") ?? "";
  const section = url.searchParams.get("section") ?? "all";
  const results = searchDocuments(query, section);

  return Response.json({
    query,
    count: results.length,
    results,
  });
}
