import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "AgentWarden | Savings dashboard",
  description: "Local observability and savings receipts for AI agents.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
