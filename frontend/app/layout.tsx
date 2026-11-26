import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Folio | Portfolio intelligence",
  description: "Understand your portfolio and its underlying exposure.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body suppressHydrationWarning>{children}</body></html>;
}
