import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "MEETME — AI Meeting Intelligence & Autonomous Execution Platform",
  description: "Transform unstructured meeting conversations into structured tasks, decisions, assignments, and automated execution workflows.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg-primary text-text-primary antialiased selection:bg-accent-orange selection:text-black">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
