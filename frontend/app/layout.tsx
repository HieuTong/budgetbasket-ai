import type { Metadata } from "next";
import {
  IBM_Plex_Mono,
  Instrument_Serif,
  Inter,
} from "next/font/google";
import "./globals.css";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-bb-sans",
});

const display = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-bb-display",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-bb-mono",
});

export const metadata: Metadata = {
  title: "BudgetBasket",
  description: "Good groceries. Better numbers.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        className={`${sans.variable} ${display.variable} ${mono.variable}`}
      >
        {children}
      </body>
    </html>
  );
}
