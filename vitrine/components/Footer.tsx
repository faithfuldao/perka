import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-[#e8ddd4] bg-[#f0e9e0] mt-auto">
      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-md bg-[#6f4e37] flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d="M3 5h12v2a6 6 0 01-12 0V5z" fill="white" />
              <path d="M13 5c0-1.1-.9-2-2-2H7a2 2 0 00-2 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M14 7c1.1 0 2 .9 2 2s-.9 2-2 2" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <rect x="6" y="13" width="6" height="1.5" rx=".75" fill="white" />
            </svg>
          </span>
          <span className="font-semibold text-[#6f4e37]">Perka</span>
        </div>

        <nav className="flex items-center gap-6" aria-label="Footer navigation">
          <Link href="/#features" className="text-sm text-[#7a6458] hover:text-[#6f4e37] transition-colors">Features</Link>
          <Link href="/#how-it-works" className="text-sm text-[#7a6458] hover:text-[#6f4e37] transition-colors">How It Works</Link>
          <Link href="/support" className="text-sm text-[#7a6458] hover:text-[#6f4e37] transition-colors">Support</Link>
        </nav>

        <p className="text-sm text-[#9e8a7e]">
          &copy; {new Date().getFullYear()} Perka. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
