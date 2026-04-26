import type { Metadata } from 'next';
import { IBM_Plex_Sans, IBM_Plex_Serif } from 'next/font/google';
import './globals.css';

const sans = IBM_Plex_Sans({
  subsets: ['latin'],
  variable: '--font-plex-sans',
  weight: ['400', '500', '600', '700'],
});

const serif = IBM_Plex_Serif({
  subsets: ['latin'],
  variable: '--font-plex-serif',
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: 'SEC Filing RAG Analyst',
  description: 'A retrieval-augmented analysis workspace for SEC 10-K and 10-Q filings.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${serif.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
