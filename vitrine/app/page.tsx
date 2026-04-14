import Link from "next/link";
import Nav from "../components/Nav";
import Footer from "../components/Footer";

function WalletIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="2" y="8" width="28" height="20" rx="4" fill="#6f4e37" opacity=".12" />
      <rect x="2" y="8" width="28" height="20" rx="4" stroke="#6f4e37" strokeWidth="2" />
      <path d="M2 14h28" stroke="#6f4e37" strokeWidth="2" />
      <circle cx="22" cy="22" r="3" fill="#f5a623" />
    </svg>
  );
}

function QrIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="11" height="11" rx="2" stroke="#6f4e37" strokeWidth="2" />
      <rect x="7" y="7" width="3" height="3" fill="#6f4e37" />
      <rect x="18" y="3" width="11" height="11" rx="2" stroke="#6f4e37" strokeWidth="2" />
      <rect x="22" y="7" width="3" height="3" fill="#6f4e37" />
      <rect x="3" y="18" width="11" height="11" rx="2" stroke="#6f4e37" strokeWidth="2" />
      <rect x="7" y="22" width="3" height="3" fill="#6f4e37" />
      <path
        d="M18 18h4v4h-4zM22 22h4v4h-4zM18 26h4"
        stroke="#6f4e37"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="9" y="2" width="14" height="28" rx="3" fill="#6f4e37" opacity=".1" />
      <rect x="9" y="2" width="14" height="28" rx="3" stroke="#6f4e37" strokeWidth="2" />
      <circle cx="16" cy="27" r="1.5" fill="#f5a623" />
      <path d="M13 6h6" stroke="#6f4e37" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function StepBadge({ n }: { n: number }) {
  return (
    <span className="w-10 h-10 rounded-full bg-[#6f4e37] text-white flex items-center justify-center font-bold text-lg shrink-0">
      {n}
    </span>
  );
}

export default function HomePage() {
  return (
    <>
      <Nav />

      <main className="flex-1">
        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden bg-gradient-to-br from-[#faf8f5] via-[#f5ede2] to-[#ede0cf] pt-24 pb-28 px-6">
          <div
            aria-hidden="true"
            className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-[#f5a623] opacity-10 blur-3xl pointer-events-none"
          />
          <div
            aria-hidden="true"
            className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-[#6f4e37] opacity-10 blur-3xl pointer-events-none"
          />

          <div className="relative max-w-4xl mx-auto text-center">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#f5a623]/20 text-[#8a5e1a] text-sm font-medium mb-6">
              <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true">
                <circle cx="4" cy="4" r="4" fill="#f5a623" />
              </svg>
              Apple &amp; Google Wallet
            </span>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-[#3b2410] leading-tight tracking-tight mb-6">
              Digital loyalty cards for your{" "}
              <span className="text-[#6f4e37]">coffee shop</span>
              <br />
              — no app required
            </h1>

            <p className="text-lg text-[#5a4a3e] max-w-2xl mx-auto mb-10 leading-relaxed">
              Perka puts a branded loyalty card directly into your customers&apos; Apple or Google
              Wallet. They earn points every visit. You keep them coming back. Zero installs, zero
              friction.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/support#contact"
                className="px-8 py-3.5 rounded-xl bg-[#6f4e37] text-white font-semibold text-base hover:bg-[#5a3e2b] transition-colors shadow-md hover:shadow-lg"
              >
                Get started free
              </Link>
              <Link
                href="/#how-it-works"
                className="px-8 py-3.5 rounded-xl border border-[#c8b09a] text-[#6f4e37] font-semibold text-base hover:bg-[#ede5db] transition-colors"
              >
                See how it works
              </Link>
            </div>
          </div>

          {/* Mock wallet card */}
          <div className="relative max-w-xs mx-auto mt-16" aria-hidden="true">
            <div className="rounded-2xl bg-gradient-to-br from-[#6f4e37] to-[#3b2410] p-6 text-white shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <p className="text-xs opacity-60 uppercase tracking-widest">Loyalty Card</p>
                  <p className="text-xl font-bold mt-0.5">Perka Coffee</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M4 7h12v2a6 6 0 01-12 0V7z" fill="white" />
                    <path
                      d="M13 7c0-1.1-.9-2-2-2H9a2 2 0 00-2 2"
                      stroke="white"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              </div>
              <div className="flex gap-1.5 mb-6 flex-wrap">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-6 h-6 rounded-full border-2 border-white/40 ${
                      i < 7 ? "bg-[#f5a623]" : "bg-white/10"
                    }`}
                  />
                ))}
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-xs opacity-60">Points</p>
                  <p className="text-2xl font-bold">7 / 10</p>
                </div>
                <div className="w-14 h-14 bg-white rounded-lg p-1.5">
                  <div className="w-full h-full grid grid-cols-4 gap-px">
                    {Array.from({ length: 16 }).map((_, i) => (
                      <div
                        key={i}
                        className={`rounded-sm ${
                          [0, 2, 5, 7, 8, 10, 13, 15, 3, 12].includes(i)
                            ? "bg-[#3b2410]"
                            : "bg-white"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute inset-0 rounded-2xl bg-[#6f4e37] blur-2xl opacity-20 -z-10 scale-90 translate-y-4" />
          </div>
        </section>

        {/* ── Features ─────────────────────────────────────────────────── */}
        <section id="features" className="py-24 px-6 bg-white">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-14">
              <h2 className="text-3xl md:text-4xl font-bold text-[#3b2410] mb-4">
                Everything you need. Nothing you don&apos;t.
              </h2>
              <p className="text-[#7a6458] text-lg max-w-xl mx-auto">
                Perka is built specifically for independent coffee shops who want a premium loyalty
                experience without the complexity.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="group rounded-2xl border border-[#e8ddd4] bg-[#faf8f5] p-8 hover:shadow-lg hover:border-[#c8b09a] transition-all">
                <div className="w-14 h-14 rounded-xl bg-[#f5ede2] flex items-center justify-center mb-5 group-hover:bg-[#ede0cf] transition-colors">
                  <WalletIcon />
                </div>
                <h3 className="text-xl font-bold text-[#3b2410] mb-3">Apple &amp; Google Wallet</h3>
                <p className="text-[#7a6458] leading-relaxed">
                  Branded passes that live natively in the apps your customers already have on their
                  phones. No new accounts, no new passwords.
                </p>
              </div>

              <div className="group rounded-2xl border border-[#e8ddd4] bg-[#faf8f5] p-8 hover:shadow-lg hover:border-[#c8b09a] transition-all">
                <div className="w-14 h-14 rounded-xl bg-[#f5ede2] flex items-center justify-center mb-5 group-hover:bg-[#ede0cf] transition-colors">
                  <QrIcon />
                </div>
                <h3 className="text-xl font-bold text-[#3b2410] mb-3">Scan &amp; Earn Points</h3>
                <p className="text-[#7a6458] leading-relaxed">
                  Staff scan the barcode on a customer&apos;s wallet pass at checkout. Points update
                  instantly, and push notifications keep customers engaged.
                </p>
              </div>

              <div className="group rounded-2xl border border-[#e8ddd4] bg-[#faf8f5] p-8 hover:shadow-lg hover:border-[#c8b09a] transition-all">
                <div className="w-14 h-14 rounded-xl bg-[#f5ede2] flex items-center justify-center mb-5 group-hover:bg-[#ede0cf] transition-colors">
                  <PhoneIcon />
                </div>
                <h3 className="text-xl font-bold text-[#3b2410] mb-3">Zero App Install</h3>
                <p className="text-[#7a6458] leading-relaxed">
                  Customers scan a QR code at your counter and tap &quot;Add to Wallet&quot;. That&apos;s it
                  — their loyalty card is set up in under 10 seconds.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── How It Works ─────────────────────────────────────────────── */}
        <section id="how-it-works" className="py-24 px-6 bg-[#faf8f5]">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-14">
              <h2 className="text-3xl md:text-4xl font-bold text-[#3b2410] mb-4">
                Up and running in minutes
              </h2>
              <p className="text-[#7a6458] text-lg max-w-xl mx-auto">
                The whole flow — from shop setup to customer earning points — takes less than a day
                to configure.
              </p>
            </div>

            <ol className="space-y-0" aria-label="How Perka works">
              <li className="flex gap-6 items-start">
                <div className="flex flex-col items-center">
                  <StepBadge n={1} />
                  <div className="w-0.5 h-16 bg-[#d4c4b5] mt-2" aria-hidden="true" />
                </div>
                <div className="pb-10 pt-1.5">
                  <h3 className="text-xl font-bold text-[#3b2410] mb-2">
                    Customer scans your QR code
                  </h3>
                  <p className="text-[#7a6458] leading-relaxed max-w-lg">
                    Place the Perka QR code on your counter, at the register, or on receipts. A
                    quick scan with any smartphone camera opens the wallet pass — no link typing
                    needed.
                  </p>
                </div>
              </li>

              <li className="flex gap-6 items-start">
                <div className="flex flex-col items-center">
                  <StepBadge n={2} />
                  <div className="w-0.5 h-16 bg-[#d4c4b5] mt-2" aria-hidden="true" />
                </div>
                <div className="pb-10 pt-1.5">
                  <h3 className="text-xl font-bold text-[#3b2410] mb-2">
                    Card is added to their wallet
                  </h3>
                  <p className="text-[#7a6458] leading-relaxed max-w-lg">
                    One tap and the branded loyalty card is saved to Apple Wallet or Google Wallet.
                    Your logo, your colors — it looks like it was built just for your shop.
                  </p>
                </div>
              </li>

              <li className="flex gap-6 items-start">
                <div className="flex flex-col items-center">
                  <StepBadge n={3} />
                </div>
                <div className="pt-1.5">
                  <h3 className="text-xl font-bold text-[#3b2410] mb-2">
                    Staff scans to award points
                  </h3>
                  <p className="text-[#7a6458] leading-relaxed max-w-lg">
                    At the next visit the customer shows their pass barcode. Staff scan it with any
                    barcode reader or phone. Points update live and a notification confirms the
                    reward.
                  </p>
                </div>
              </li>
            </ol>
          </div>
        </section>

        {/* ── Stats strip ──────────────────────────────────────────────── */}
        <section className="bg-white py-14 px-6 border-y border-[#e8ddd4]">
          <div className="max-w-5xl mx-auto">
            <p className="text-center text-sm font-medium text-[#9e8a7e] uppercase tracking-widest mb-8">
              Why coffee shops choose Perka
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
              <div>
                <p className="text-4xl font-bold text-[#6f4e37] mb-1">10 sec</p>
                <p className="text-[#7a6458] text-sm">Average card setup time for a customer</p>
              </div>
              <div>
                <p className="text-4xl font-bold text-[#6f4e37] mb-1">0</p>
                <p className="text-[#7a6458] text-sm">App downloads required — ever</p>
              </div>
              <div>
                <p className="text-4xl font-bold text-[#6f4e37] mb-1">100%</p>
                <p className="text-[#7a6458] text-sm">Branded with your shop&apos;s identity</p>
              </div>
            </div>
          </div>
        </section>

        {/* ── CTA ──────────────────────────────────────────────────────── */}
        <section className="py-24 px-6 bg-gradient-to-br from-[#6f4e37] to-[#3b2410] text-white text-center">
          <div className="max-w-2xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-bold mb-5">Ready to reward your regulars?</h2>
            <p className="text-lg text-white/75 mb-10">
              Get in touch and we&apos;ll have your digital loyalty card live in your customers&apos;
              wallets within 24 hours.
            </p>
            <Link
              href="/support#contact"
              className="inline-block px-10 py-4 rounded-xl bg-[#f5a623] text-[#3b2410] font-bold text-base hover:bg-[#e09415] transition-colors shadow-lg"
            >
              Get started — it&apos;s free
            </Link>
            <p className="text-sm text-white/50 mt-5">No credit card required. No commitment.</p>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
