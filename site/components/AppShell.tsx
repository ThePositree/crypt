import Link from "next/link";
import { ReactNode } from "react";
import { ArrowRight, Github, Menu } from "lucide-react";
import { topicNav } from "@/lib/content";
import { SearchBox } from "./SearchBox";
import { VersionSelector } from "./VersionSelector";
import { Mascot } from "./Mascot";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="site-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">c</span>
          <span>
            <strong>crypt</strong>
            <small>Docs Town</small>
          </span>
        </Link>
        <SearchBox />
        <nav className="top-actions" aria-label="Site controls">
          <VersionSelector />
          <Link className="icon-link" href="https://github.com/ThePositree/crypt" aria-label="Source repository">
            <Github size={18} />
          </Link>
          <button className="icon-link mobile-menu" type="button" aria-label="Open navigation">
            <Menu size={18} />
          </button>
        </nav>
      </header>

      <div className="shell-grid">
        <aside className="sidebar">
          <nav aria-label="Topic navigation">
            <p className="nav-kicker">Topics</p>
            {topicNav.map((item) => {
              const Icon = item.icon;
              return (
                <Link href={`/docs/${item.slug}`} key={item.slug}>
                  <Icon size={17} aria-hidden="true" />
                  {item.title}
                </Link>
              );
            })}
          </nav>

          <div className="helper-card">
            <Mascot mood="reader" />
            <strong>Need a route?</strong>
            <p>Start with the map, then follow a topic, journey, or search result.</p>
            <Link href="/docs/overview">
              Open overview <ArrowRight size={14} />
            </Link>
          </div>
        </aside>

        <main className="content-frame">{children}</main>
      </div>
    </div>
  );
}
