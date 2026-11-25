import type { Metadata } from "next";
import { Suspense } from "react";
import { Figtree, Schibsted_Grotesk } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const head = Schibsted_Grotesk({ subsets: ["latin"], variable: "--font-head", weight: ["600", "700"] });
const body = Figtree({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: { default: "TaskVise - Tasks, projects and workload for your whole team", template: "%s | TaskVise" },
  description: "Assign tasks, track projects, balance workload and handle leave, with a view for every role.",
  icons: { icon: [{ url: "/favicon.ico", sizes: "any" }, { url: "/favicon-32.png", type: "image/png", sizes: "32x32" }], apple: "/apple-touch-icon.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${head.variable} ${body.variable}`}>
      <body className="antialiased">
        <AuthProvider>
          <Suspense fallback={null}>{children}</Suspense>
        </AuthProvider>
      </body>
    </html>
  );
}
