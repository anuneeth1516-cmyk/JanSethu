import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "jansethu | Turn problems into progress", description: "AI-powered civic collaboration." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}