import { Home, Gauge, TrendingUp, Target, Users, DollarSign, LineChart, FlaskConical, Beaker, BrainCircuit, Radar, HeartPulse, FileText, Database, Settings, Bot } from "lucide-react";
export const NAV = [
  { section: "OVERVIEW", items: [
    { href: "/", label: "Home", icon: Home, desc: "Command centre" },
    { href: "/executive", label: "Executive Intelligence", icon: Gauge, desc: "Scorecard & targets" }] },
  { section: "ANALYTICS", items: [
    { href: "/growth", label: "Business Growth", icon: TrendingUp, desc: "Revenue drivers" },
    { href: "/marketing", label: "Marketing Intelligence", icon: Target, desc: "Channels & budget" },
    { href: "/customers", label: "Customer Intelligence", icon: Users, desc: "Segments & churn" },
    { href: "/pricing", label: "Pricing & Profitability", icon: DollarSign, desc: "Scenarios & margin" }] },
  { section: "PREDICTION & PLANNING", items: [
    { href: "/forecasting", label: "Demand Forecasting", icon: LineChart, desc: "Outlook & inventory" },
    { href: "/mmm", label: "Marketing Mix Modeling", icon: FlaskConical, desc: "Readiness-gated" },
    { href: "/experiments", label: "Experimentation Lab", icon: Beaker, desc: "A/B & causal" }] },
  { section: "INTELLIGENCE", items: [
    { href: "/decisions", label: "Decision Intelligence", icon: BrainCircuit, desc: "Act & track outcomes", badge: true },
    { href: "/market-radar", label: "Market Radar", icon: Radar, desc: "Competitor snapshots" },
    { href: "/health", label: "Data & Model Health", icon: HeartPulse, desc: "Quality & drift" }] },
  { section: "WORKSPACE", items: [
    { href: "/reports", label: "Reports", icon: FileText, desc: "Executive exports" },
    { href: "/data-sources", label: "Data Sources", icon: Database, desc: "Upload & schemas" },
    { href: "/settings", label: "Settings", icon: Settings, desc: "Preferences" }] },
];
export const ALL_ROUTES = NAV.flatMap((g) => g.items);
export const COPILOT_ICON = Bot;
