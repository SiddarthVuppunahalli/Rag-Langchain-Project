import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'IT Helpdesk RAG Assistant',
  description: 'AI-powered IT troubleshooting bot',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900 min-h-screen flex flex-col`}>
        <main className="flex-1 flex flex-col max-w-5xl mx-auto w-full p-4 md:p-8">
          {children}
        </main>
      </body>
    </html>
  )
}
