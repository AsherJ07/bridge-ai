import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import "@fontsource-variable/manrope";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bridge — Understand more than words",
  description: "Evidence-grounded cultural context for short-form video.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="wordmark" aria-label="Bridge home">
            <span className="brand-glyph" aria-hidden="true">B</span>
            <span>BRIDGE</span>
          </Link>
          <nav aria-label="Primary navigation">
            <Link href="/analyze">Analyze</Link>
            <Link href="/evaluation">Evaluation</Link>
            <a
              href="https://github.com/AsherJ07/bridge-ai"
              target="_blank"
              rel="noreferrer"
              className="nav-source"
            >
              Source <ArrowUpRight size={14} aria-hidden="true" />
            </a>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
