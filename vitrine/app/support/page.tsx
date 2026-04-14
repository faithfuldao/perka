import type { Metadata } from "next";
import Link from "next/link";
import Nav from "../../components/Nav";
import Footer from "../../components/Footer";
import ContactForm from "../../components/ContactForm";

export const metadata: Metadata = {
  title: "Support — Perka",
  description: "Get help with your Perka digital loyalty card. Browse FAQs or contact our team.",
};

const faqs: { q: string; a: string }[] = [
  {
    q: "How do I add my Perka loyalty card to my phone?",
    a: "Ask the staff at your coffee shop for the Perka QR code — it is usually displayed at the counter or printed on a receipt. Scan it with your phone's camera app and tap the link that appears. You will be taken straight to Apple Wallet or Google Wallet where you can add the card with one tap.",
  },
  {
    q: "My points are not updating after a visit. What should I do?",
    a: "Points are added when staff scan the barcode on your wallet card. Make sure you open the card from your wallet app and show the barcode to the staff member before paying. If points still have not appeared after a few minutes, ask the barista to rescan — occasionally a noisy environment can cause a misread.",
  },
  {
    q: "I lost my phone. Can I recover my loyalty card and points?",
    a: "Yes. Your points balance is stored on our servers, not only on your device. Contact us using the form below with your email address or the phone number you registered with, and we will help you restore your card to a new device.",
  },
  {
    q: "Can I use my card at multiple locations of the same coffee shop?",
    a: "Absolutely. If the coffee shop uses Perka across all their branches, your card and points balance work everywhere. Each shop manages their own program, so check with your shop if you are unsure whether a specific branch is enrolled.",
  },
  {
    q: "How do I redeem my free coffee reward?",
    a: "When you reach the reward threshold (for example 10 points), your card updates automatically and shows a reward notification. Simply show your card at the counter — the staff will scan it to apply the reward and reset your points counter for the next round.",
  },
  {
    q: "I am a coffee shop owner. How do I get started with Perka?",
    a: "Fill in the contact form below with a brief description of your shop and we will set up a branded loyalty card for you, usually within 24 hours. There is nothing to install on your end — you will receive a QR code to display and a simple scanning tool for your staff.",
  },
];

function ChevronIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
      className="shrink-0 text-[#6f4e37]"
    >
      <path
        d="M4.5 6.75L9 11.25L13.5 6.75"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function SupportPage() {
  return (
    <>
      <Nav />

      <main className="flex-1">
        {/* Page header */}
        <section className="bg-gradient-to-br from-[#faf8f5] to-[#f0e9e0] py-20 px-6 border-b border-[#e8ddd4]">
          <div className="max-w-3xl mx-auto text-center">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6f4e37]/10 text-[#6f4e37] text-sm font-medium mb-5">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="6" stroke="#6f4e37" strokeWidth="1.5" />
                <path
                  d="M7 5v3M7 9.5v.5"
                  stroke="#6f4e37"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              Support
            </span>
            <h1 className="text-4xl md:text-5xl font-bold text-[#3b2410] mb-4">
              How can we help?
            </h1>
            <p className="text-lg text-[#7a6458] max-w-xl mx-auto">
              Browse the frequently asked questions below, or send us a message and we will get back
              to you within one business day.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 px-6 bg-white" aria-labelledby="faq-heading">
          <div className="max-w-3xl mx-auto">
            <h2
              id="faq-heading"
              className="text-2xl md:text-3xl font-bold text-[#3b2410] mb-10"
            >
              Frequently asked questions
            </h2>

            <dl className="divide-y divide-[#e8ddd4]">
              {faqs.map((item, i) => (
                <details key={i} className="group py-5" name="faq">
                  <summary className="flex items-center justify-between gap-4 cursor-pointer list-none select-none">
                    <dt className="text-base font-semibold text-[#3b2410] group-open:text-[#6f4e37] transition-colors">
                      {item.q}
                    </dt>
                    <span className="transition-transform group-open:rotate-180">
                      <ChevronIcon />
                    </span>
                  </summary>
                  <dd className="mt-3 text-[#7a6458] leading-relaxed text-sm pr-8">{item.a}</dd>
                </details>
              ))}
            </dl>
          </div>
        </section>

        {/* Contact form */}
        <section
          id="contact"
          className="py-20 px-6 bg-[#faf8f5] border-t border-[#e8ddd4]"
          aria-labelledby="contact-heading"
        >
          <div className="max-w-2xl mx-auto">
            <div className="mb-10">
              <h2
                id="contact-heading"
                className="text-2xl md:text-3xl font-bold text-[#3b2410] mb-3"
              >
                Contact us
              </h2>
              <p className="text-[#7a6458]">
                Can&apos;t find the answer above? Drop us a message and a real human will reply
                soon.
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-[#e8ddd4] p-8 shadow-sm">
              <ContactForm />
            </div>
          </div>
        </section>

        {/* Back to home */}
        <div className="py-10 px-6 text-center bg-white border-t border-[#e8ddd4]">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#6f4e37] hover:text-[#5a3e2b] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M10 12L6 8l4-4"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Back to homepage
          </Link>
        </div>
      </main>

      <Footer />
    </>
  );
}
