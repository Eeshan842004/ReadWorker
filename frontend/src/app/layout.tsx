import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { NavLinks } from "@/components/NavLinks";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agentic Knowledge Worker",
  description: "Multi-agent RAG with hybrid retrieval, live chunking, and cited answers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-30 border-b border-border/70 bg-background/80 backdrop-blur-md">
          <nav className="mx-auto flex w-full max-w-5xl items-center gap-4 px-4 py-2.5">
            <Link href="/" className="ak-transition flex items-center gap-2 hover:opacity-80">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-sm shadow-sm">
                🧠
              </span>
              <span className="text-sm font-semibold tracking-tight">Knowledge Worker</span>
            </Link>
            <div className="ml-auto">
              <NavLinks />
            </div>
          </nav>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>

        <footer className="border-t border-border/70 py-3">
          <p className="mx-auto max-w-5xl px-4 text-[11px] text-muted-foreground">
            Groq · Gemini embeddings · pgvector · LangGraph — grounded, cited, zero API cost.
          </p>
        </footer>
      </body>
    </html>
  );
}
