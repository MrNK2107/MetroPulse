import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MetroPulse — Urban Digital Twin Sandbox",
  description: "AI-Powered Macro-Urban Digital Twin Sandbox",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-dark-300 text-gray-200`}>
        {children}
      </body>
    </html>
  );
}
