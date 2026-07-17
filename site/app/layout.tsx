import type { Metadata } from "next";
import "./site.css";

export const metadata: Metadata = {
  title: "AgentWarden | Make every agent request count",
  description: "The local, OpenAI-compatible proxy that removes agent context waste and proves behavior held.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
