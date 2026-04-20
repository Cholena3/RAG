import type { Metadata } from "next";
import "./globals.css";
import "highlight.js/styles/github-dark.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "DocMind — Intelligent Document Q&A",
  description: "Upload documents, ask questions, get cited answers powered by local LLMs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
