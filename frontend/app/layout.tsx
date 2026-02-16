import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { Providers } from "@/components/providers";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Tickets - Discover Amazing Events",
    template: "%s | Tickets",
  },
  description: "Find and purchase tickets to the best events near you",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "https://ai-tickets.fly.dev"
  ),
  openGraph: {
    type: "website",
    siteName: "Tickets",
    locale: "en_US",
  },
  twitter: {
    card: "summary",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
