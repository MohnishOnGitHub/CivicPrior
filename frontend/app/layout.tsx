import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CivicPrior — Policy dashboard",
  description: "Evidence-derived infrastructure allocation for civic decision-makers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
