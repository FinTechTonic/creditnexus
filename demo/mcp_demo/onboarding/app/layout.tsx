import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CreditNexus MCP Onboarding",
  description: "Payment-protected tools for AI agents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
