import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASC - Autonomous Software Company",
  description: "A production-grade multi-agent AI platform that functions like a complete software company.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-50 text-surface-900 antialiased">
        {children}
      </body>
    </html>
  );
}