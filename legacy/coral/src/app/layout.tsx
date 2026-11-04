import type { Metadata } from "next";
import Link from "next/link";
import { PRODUCT } from "@/lib/config";
import "./globals.css";

export const metadata: Metadata = {
  title: `${PRODUCT.name} — ${PRODUCT.tagline}`,
  description:
    "Five open-weight models. Weights stored in Australia, running on Australian AI compute, " +
    "served through one Australian API for Australian businesses and enterprises.",
};

function TopBar() {
  return (
    <header className="topbar">
      <div className="wrap">
        <Link href="/" className="brand">
          <span className="brand-mark" aria-hidden />
          {PRODUCT.name}
          <small>AU</small>
        </Link>
        <nav className="navlinks">
          <Link href="/#models">Models</Link>
          <Link href="/#sovereignty">Sovereignty</Link>
          <Link href="/docs">Docs</Link>
        </nav>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-AU">
      <body>
        <TopBar />
        {children}
        <footer>
          <div className="wrap">
            <span>
              {PRODUCT.legalName} — {PRODUCT.tagline}
            </span>
            <span>
              Model weights stored in Australia · Inference on Australian compute · No offshore
              fallback
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
