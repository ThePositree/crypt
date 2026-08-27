import { slugify } from "@/lib/docs";

export function MarkdownContent({ content }: { content: string }) {
  const blocks = parseMarkdown(content);

  return (
    <article className="prose-docs">
      {blocks.map((block, index) => renderBlock(block, index))}
    </article>
  );
}

type Block =
  | { type: "heading"; depth: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "code"; language: string; code: string }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "quote"; text: string }
  | { type: "rule" };

function parseMarkdown(markdown: string): Block[] {
  const lines = markdown.split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const language = line.slice(3).trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: "code", language, code: code.join("\n") });
      index += 1;
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push({ type: "heading", depth: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }

    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }

    if (line.startsWith(">")) {
      const quote: string[] = [];
      while (index < lines.length && lines[index].startsWith(">")) {
        quote.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", text: quote.join(" ") });
      continue;
    }

    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items: string[] = [];
      while (
        index < lines.length &&
        (ordered ? /^\s*\d+\.\s+/.test(lines[index]) : /^\s*[-*]\s+/.test(lines[index]))
      ) {
        items.push(lines[index].replace(/^\s*(?:[-*]|\d+\.)\s+/, ""));
        index += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    if (isTableStart(lines, index)) {
      const headers = splitTableRow(lines[index]);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && /^\s*\|/.test(lines[index])) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push({ type: "table", headers, rows });
      continue;
    }

    const paragraph: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].startsWith("```") &&
      !/^(#{1,4})\s+/.test(lines[index]) &&
      !/^\s*[-*]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index]) &&
      !lines[index].startsWith(">")
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}

function renderBlock(block: Block, index: number) {
  switch (block.type) {
    case "heading": {
      const id = slugify(block.text);
      const children = renderInline(block.text);
      if (block.depth === 1) {
        return <h1 key={index}>{children}</h1>;
      }
      if (block.depth === 2) {
        return (
          <h2 id={id} key={index}>
            {children}
          </h2>
        );
      }
      return (
        <h3 id={id} key={index}>
          {children}
        </h3>
      );
    }
    case "paragraph":
      return <p key={index}>{renderInline(block.text)}</p>;
    case "list": {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag key={index}>
          {block.items.map((item) => (
            <li key={item}>{renderInline(item)}</li>
          ))}
        </ListTag>
      );
    }
    case "code":
      return (
        <div className="code-frame" key={index}>
          {block.language ? <div className="code-language">{block.language}</div> : null}
          <pre>
            <code>{block.code}</code>
          </pre>
        </div>
      );
    case "table":
      return (
        <table key={index}>
          <thead>
            <tr>
              {block.headers.map((header) => (
                <th key={header}>{renderInline(header)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={`${row.join("-")}-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`${cell}-${cellIndex}`}>{renderInline(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    case "quote":
      return <blockquote key={index}>{renderInline(block.text)}</blockquote>;
    case "rule":
      return <hr key={index} />;
  }
}

function isTableStart(lines: string[], index: number): boolean {
  const current = lines[index];
  const next = lines[index + 1];
  return Boolean(current?.trim().startsWith("|") && next && /^\s*\|?[\s:-]+\|[\s|:-]*$/.test(next));
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderInline(text: string) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+]\([^)]+\))/g);

  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    const link = /^\[([^\]]+)]\(([^)]+)\)$/.exec(part);
    if (link) {
      return (
        <a
          className="font-medium text-[#33758a] underline decoration-[#77b6cb]/45 underline-offset-4 hover:text-[#23576a]"
          href={link[2]}
          key={`${part}-${index}`}
        >
          {link[1]}
        </a>
      );
    }
    return part;
  });
}
