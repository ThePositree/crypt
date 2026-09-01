"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Moon, Search, Sun, X } from "lucide-react";
import { useEffect, useState } from "react";
import { sections } from "@/lib/content";
import { SearchDialog } from "@/components/search-dialog";

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);
  const [treeOpen, setTreeOpen] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <>
      <header className="topbar">
        <Link href="/" className="brand" aria-label="crypt docs home">
          <span className="brand-mark">cd</span>
          <span>crypt docs</span>
        </Link>
        <nav className="topnav" aria-label="Главные разделы">
          {sections.slice(0, 8).map((section) => {
            const Icon = section.icon;
            return (
              <Link
                key={section.id}
                href={section.href}
                className={pathname === section.href ? "active" : ""}
              >
                <Icon size={16} />
                <span>{section.shortTitle}</span>
              </Link>
            );
          })}
        </nav>
        <div className="top-actions">
          <button className="search-button" type="button" onClick={() => setSearchOpen(true)}>
            <Search size={17} />
            <span>Поиск</span>
            <kbd>⌘K</kbd>
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={() => setDark((value) => !value)}
            aria-label="Переключить тему"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            className="icon-button mobile-only"
            type="button"
            onClick={() => setTreeOpen((value) => !value)}
            aria-label="Открыть навигацию"
          >
            {treeOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </header>
      <div className="portal-layout">
        <aside className={`left-tree ${treeOpen ? "open" : ""}`} aria-label="Дерево документации">
          <p className="tree-title">Документация</p>
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <Link
                key={section.id}
                href={section.href}
                onClick={() => setTreeOpen(false)}
                className={pathname === section.href ? "active" : ""}
              >
                <Icon size={16} />
                <span>{section.title}</span>
              </Link>
            );
          })}
          <div className="helper-card">
            <span className="character-dot">?</span>
            <strong>Нужна ориентация?</strong>
            <p>Начни с карты системы или открой путь сигнала.</p>
          </div>
        </aside>
        <main className="content-shell">{children}</main>
      </div>
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
