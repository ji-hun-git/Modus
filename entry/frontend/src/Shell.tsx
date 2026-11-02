import { useRef, useState } from "react";
import {
  CalendarDays,
  Files,
  GitCompareArrows,
  History,
  House,
  Info,
  ChartNoAxesCombined,
  MoreHorizontal,
  MessageCircle,
  Plus,
  FileText,
  PanelLeftClose,
  PanelLeftOpen,
  SunMoon,
} from "lucide-react";
import { Brand } from "./ui";
import AboutWorkspaceDialog from "./AboutWorkspaceDialog";
import useAppearance, { type Appearance } from "./useAppearance";

export type Page =
  | "Home"
  | "Timeline"
  | "Replay"
  | "Records"
  | "Measurements"
  | "Changes"
  | "Brief"
  | "Ask";
const pages = [
  { page: "Home" as const, label: "Home", icon: House },
  { page: "Timeline" as const, label: "Records", icon: CalendarDays },
];
const moreTools = [
  { page: "Ask" as const, label: "Ask", icon: MessageCircle },
  { page: "Brief" as const, label: "Brief", icon: FileText },
  { page: "Measurements" as const, label: "Trends", icon: ChartNoAxesCombined },
  { page: "Records" as const, label: "Documents", icon: Files },
  {
    page: "Replay" as const,
    label: "Replay",
    icon: GitCompareArrows,
  },
  { page: "Changes" as const, label: "Changes", icon: History },
];
const pageTitle = {
  Home: "Your records",
  Timeline: "Your records",
  Records: "Your documents",
  Measurements: "Your history over time",
  Replay: "Past records",
  Changes: "Activity",
  Brief: "Prepare a brief",
  Ask: "Ask your history",
};

export default function Shell({
  page,
  setPage,
  onImport,
  hasDraft,
  children,
}: {
  page: Page;
  setPage: (page: Page) => void;
  onImport: () => void;
  hasDraft: boolean;
  children: React.ReactNode;
}) {
  const [aboutOpen, setAboutOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [appearance, setAppearance] = useAppearance();
  const toolsRef = useRef<HTMLDetailsElement>(null);
  const appearanceControl = (
    <label className="appearance-control">
      <SunMoon size={16} aria-hidden="true" />
      <span>Appearance</span>
      <select aria-label="Appearance" value={appearance}
        onChange={(event) => setAppearance(event.target.value as Appearance)}>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
        <option value="system">System</option>
      </select>
    </label>
  );
  const demoControl = (
    <button
      className="demo-control"
      onClick={() => setAboutOpen(true)}
      aria-haspopup="dialog"
      aria-label="Demo data: about this data"
      title="About this example workspace"
    >
      <Info size={15} strokeWidth={1.5} aria-hidden="true" focusable="false" />
      <span>Demo data</span>
    </button>
  );
  const moreControl = (
    <details
      ref={toolsRef}
      className={
        "history-tools nav-more " +
        (!pages.some((item) => item.page === page) ? "active-tools" : "")
      }
      onKeyDown={(event) => {
        if (event.key === "Escape" && toolsRef.current?.open) {
          toolsRef.current.open = false;
          toolsRef.current.querySelector("summary")?.focus();
        }
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null))
          event.currentTarget.open = false;
      }}
    >
      <summary aria-label="More: Ask, Brief, Trends, Documents, Replay, Changes">
        <MoreHorizontal size={18} strokeWidth={1.5} aria-hidden="true" focusable="false" />
        <span>More</span>
      </summary>
      <div className="history-tools-menu" role="group" aria-label="More views">
        {moreTools.map(({ page: destination, label, icon: Icon }) => (
          <button
            key={destination}
            aria-current={page === destination ? "page" : undefined}
            onClick={() => {
              setPage(destination);
              if (toolsRef.current) {
                toolsRef.current.open = false;
                toolsRef.current.querySelector("summary")?.focus();
              }
            }}
          >
            <Icon size={17} strokeWidth={1.5} aria-hidden="true" focusable="false" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </details>
  );
  return (
    <>
      <div className={`app-layout mission-shell workspace-shell orbit-theme${sidebarCollapsed ? " sidebar-collapsed" : ""}${page === "Home" ? " orbit-home" : page === "Ask" ? " orbit-ask" : ""}`}>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <header className="mobile-header">
          <Brand />
          <div className="mobile-utilities">{appearanceControl}{demoControl}</div>
        </header>
        <aside className="sidebar">
          <div className="sidebar-heading">
            <Brand />
            <button className="sidebar-toggle" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-expanded={!sidebarCollapsed}>
              {sidebarCollapsed ? <PanelLeftOpen size={18} aria-hidden="true" /> : <PanelLeftClose size={18} aria-hidden="true" />}
            </button>
          </div>
          <nav aria-label="Main navigation">
            {pages.map(({ page: destination, label, icon: Icon }) => (
              <button
                key={label}
                aria-label={label}
                title={sidebarCollapsed ? label : undefined}
                aria-current={page === destination ? "page" : undefined}
                className={page === destination ? "active" : ""}
                onClick={() => {
                  setPage(destination);
                  if (toolsRef.current) toolsRef.current.open = false;
                }}
              >
                <Icon size={18} strokeWidth={1.5} aria-hidden="true" focusable="false" />
                <span className="nav-label-desktop">{label}</span>
                <span className="nav-label-mobile">{label}</span>
              </button>
            ))}
            {moreControl}
          </nav>
          <div className="workspace-label">
            {appearanceControl}
            <span className="workspace-about">{demoControl}</span>
          </div>
        </aside>
        <div className="workspace">
          <main
            id="main-content"
            className={page === "Home" ? "home-page" : undefined}
            tabIndex={-1}
          >
            {page !== "Home" && <div className="page-header">
              <div>
                <h1>{pageTitle[page]}</h1>
              </div>
              <div className="header-actions">
                  <button className="primary" onClick={onImport}>
                    <Plus size={18} strokeWidth={1.5} aria-hidden="true" focusable="false" />
                    {hasDraft ? "Continue review" : "Add records"}
                  </button>
              </div>
            </div>}
            {children}
          </main>
        </div>
      </div>
      {aboutOpen && <AboutWorkspaceDialog onClose={() => setAboutOpen(false)} />}
    </>
  );
}
