"use client";

import Link from "next/link";
import { useState } from "react";

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-[#faf8f5]/90 backdrop-blur border-b border-[#e8ddd4]">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <span className="w-8 h-8 rounded-lg bg-[#6f4e37] flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d="M3 5h12v2a6 6 0 01-12 0V5z" fill="white" />
              <path d="M13 5c0-1.1-.9-2-2-2H7a2 2 0 00-2 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M14 7c1.1 0 2 .9 2 2s-.9 2-2 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <rect x="6" y="13" width="6" height="1.5" rx=".75" fill="white" />
            </svg>
          </span>
          <span className="font-semibold text-xl tracking-tight text-[#6f4e37] group-hover:text-[#5a3e2b] transition-colors">
            Perka
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8" aria-label="Main navigation">
          <Link href="/#features" className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37] transition-colors">
            Features
          </Link>
          <Link href="/#how-it-works" className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37] transition-colors">
            How It Works
          </Link>
          <Link href="/support" className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37] transition-colors">
            Support
          </Link>
          <Link
            href="/support#contact"
            className="px-4 py-2 rounded-lg bg-[#6f4e37] text-white text-sm font-medium hover:bg-[#5a3e2b] transition-colors"
          >
            Get started
          </Link>
        </nav>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-md hover:bg-[#ede5db] transition-colors"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M4 4l12 12M16 4L4 16" stroke="#6f4e37" strokeWidth="2" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="#6f4e37" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-[#e8ddd4] bg-[#faf8f5] px-6 py-4 flex flex-col gap-4">
          <Link href="/#features" onClick={() => setOpen(false)} className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37]">Features</Link>
          <Link href="/#how-it-works" onClick={() => setOpen(false)} className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37]">How It Works</Link>
          <Link href="/support" onClick={() => setOpen(false)} className="text-sm font-medium text-[#5a4a3e] hover:text-[#6f4e37]">Support</Link>
          <Link
            href="/support#contact"
            onClick={() => setOpen(false)}
            className="self-start px-4 py-2 rounded-lg bg-[#6f4e37] text-white text-sm font-medium hover:bg-[#5a3e2b] transition-colors"
          >
            Get started
          </Link>
        </div>
      )}
    </header>
  );
}
