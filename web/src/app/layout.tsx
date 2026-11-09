import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CampusAsk | University of Central Missouri",
  description:
    "Official UCM policy answers, grounded in the undergraduate and graduate catalogs.",
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
