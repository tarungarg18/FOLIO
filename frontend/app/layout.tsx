import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "FOLIO — Your money, understood", description: "Portfolio intelligence for Indian investors" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
