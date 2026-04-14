"use client";

import { useState, FormEvent } from "react";

type FormState = "idle" | "submitting" | "success";

export default function ContactForm() {
  const [formState, setFormState] = useState<FormState>("idle");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormState("submitting");
    // Simulate a short delay then show success (static — no backend)
    setTimeout(() => {
      setFormState("success");
      setName("");
      setEmail("");
      setMessage("");
    }, 800);
  }

  if (formState === "success") {
    return (
      <div
        role="alert"
        className="rounded-2xl bg-[#f0faf4] border border-[#a3d9b1] p-8 text-center"
      >
        <div className="w-12 h-12 rounded-full bg-[#22c55e]/15 flex items-center justify-center mx-auto mb-4">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M5 12l5 5L19 7"
              stroke="#16a34a"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h3 className="text-xl font-bold text-[#166534] mb-2">Message received!</h3>
        <p className="text-[#4ade80]/80 text-[#15803d]">
          Thanks for reaching out. We&apos;ll get back to you within one business day.
        </p>
        <button
          onClick={() => setFormState("idle")}
          className="mt-6 text-sm font-medium text-[#6f4e37] underline underline-offset-2 hover:text-[#5a3e2b] transition-colors"
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div>
        <label htmlFor="contact-name" className="block text-sm font-medium text-[#3b2410] mb-1.5">
          Name
        </label>
        <input
          id="contact-name"
          type="text"
          required
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          className="w-full px-4 py-3 rounded-xl border border-[#d4c4b5] bg-white text-[#1a1009] placeholder:text-[#b0a097] focus:outline-none focus:ring-2 focus:ring-[#6f4e37] focus:border-transparent transition"
        />
      </div>

      <div>
        <label htmlFor="contact-email" className="block text-sm font-medium text-[#3b2410] mb-1.5">
          Email address
        </label>
        <input
          id="contact-email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-4 py-3 rounded-xl border border-[#d4c4b5] bg-white text-[#1a1009] placeholder:text-[#b0a097] focus:outline-none focus:ring-2 focus:ring-[#6f4e37] focus:border-transparent transition"
        />
      </div>

      <div>
        <label
          htmlFor="contact-message"
          className="block text-sm font-medium text-[#3b2410] mb-1.5"
        >
          Message
        </label>
        <textarea
          id="contact-message"
          required
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Tell us about your coffee shop or describe your issue..."
          className="w-full px-4 py-3 rounded-xl border border-[#d4c4b5] bg-white text-[#1a1009] placeholder:text-[#b0a097] focus:outline-none focus:ring-2 focus:ring-[#6f4e37] focus:border-transparent transition resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={formState === "submitting"}
        className="w-full py-3.5 rounded-xl bg-[#6f4e37] text-white font-semibold hover:bg-[#5a3e2b] disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
      >
        {formState === "submitting" ? "Sending..." : "Send message"}
      </button>

      <p className="text-xs text-[#9e8a7e] text-center">
        We&apos;ll get back to you within one business day.
      </p>
    </form>
  );
}
