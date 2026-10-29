import "@fontsource-variable/inter";
import "./globals.css";
import Shell from "@/components/Shell";
export const metadata = { title: "CORTEXORA — The Intelligence Engine for Predictive Business Decisions", description: "Predict the Future. Optimize the Present. Engineer Business Growth." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en" className="dark"><body><Shell>{children}</Shell></body></html>);
}
