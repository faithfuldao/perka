import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Perka — Digital Loyalty Cards for Coffee Shops",
  description:
    "Perka lets coffee shops offer branded digital loyalty cards on Apple Wallet and Google Wallet. No app required for your customers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geist.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#faf8f5] text-[#1a1009]">
        {children}
      </body>
    </html>
  );
}
