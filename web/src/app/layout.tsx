import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CampusAsk | University of Central Missouri",
  description:
    "Official UCM policy answers, grounded in the undergraduate and graduate catalogs.",
};

/** Keep CampusAsk on the light UCM brand palette even when the OS prefers dark. */
export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#fbf6f4",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="light">
      <body>{children}</body>
    </html>
  );
}
