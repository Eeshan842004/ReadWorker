"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Upload" },
  { href: "/chat", label: "Chat" },
  { href: "/documents", label: "Documents" },
  { href: "/eval", label: "Eval" },
  { href: "/traces", label: "Traces" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <div className="flex items-center gap-1">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`ak-transition relative rounded-full px-3 py-1.5 text-sm ${
              active
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:bg-card/60 hover:text-foreground"
            }`}
          >
            {link.label}
            {active ? (
              <span className="absolute inset-x-3 -bottom-px h-px bg-brand/60" />
            ) : null}
          </Link>
        );
      })}
    </div>
  );
}
