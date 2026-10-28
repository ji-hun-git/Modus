import { useRef, useState } from "react";
import {
  ArrowUpRight,
  CalendarDays,
  Files,
  GitCompareArrows,
  History,
  House,
  Info,
  ChartNoAxesCombined,
  MoreHorizontal,
  Plus,
} from "lucide-react";
import { Brand, Modal } from "./ui";

export type Page =
  "Home" | "Timeline" | "Replay" | "Records" | "Measurements" | "Changes";
const pages = [
  { page: "Home" as const, label: "Overview", icon: House },
  { page: "Timeline" as const, label: "Records", icon: CalendarDays },
  { page: "Measurements" as const, label: "Trends", icon: ChartNoAxesCombined },
  { page: "Records" as const, label: "Documents", icon: Files },
];
const historyTools = [
  {
    page: "Replay" as const,
    label: "View past records",
    icon: GitCompareArrows,
  },
  { page: "Changes" as const, label: "Upload activity", icon: History },
];
const pageTitle = {
  Home: "Your health records",
  Timeline: "Your records",
  Records: "Your documents",
  Measurements: "Measurement history",
  Replay: "Past records",
  Changes: "Activity",
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
  const toolsRef = useRef<HTMLDetailsElement>(null);
  const demoControl = (
    <button
      className="demo-control"
      onClick={() => setAboutOpen(true)}
      aria-haspopup="dialog"
      aria-label="Demo data: about this data"
    >
      <Info size={15} />
      <span>Demo data</span>
    </button>
  );
  return (
    <>
      <div className="app-layout">
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <header className="mobile-header">
          <Brand />
          {demoControl}
        </header>
        <aside className="sidebar">
          <Brand />
          <nav aria-label="Main navigation">
            {pages.map(({ page: destination, label, icon: Icon }) => (
              <button
                key={label}
                aria-label={label}
                aria-current={page === destination ? "page" : undefined}
                className={page === destination ? "active" : ""}
                onClick={() => {
                  setPage(destination);
                  if (toolsRef.current) toolsRef.current.open = false;
                }}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span>{label}</span>
              </button>
            ))}
            <details
              ref={toolsRef}
              className={
                "history-tools " +
                (!["Home", "Timeline", "Records", "Measurements"].includes(page)
                  ? "active-tools"
                  : "")
              }
              onKeyDown={(event) => {
                if (event.key === "Escape" && toolsRef.current?.open) {
                  toolsRef.current.open = false;
                  toolsRef.current.querySelector("summary")?.focus();
                }
              }}
              onBlur={(event) => {
                if (
                  !event.currentTarget.contains(
                    event.relatedTarget as Node | null,
                  )
                )
                  event.currentTarget.open = false;
              }}
            >
              <summary>
                <MoreHorizontal size={18} />
                <span>Past views</span>
              </summary>
              <div
                className="history-tools-menu"
                aria-label="Past views and activity"
              >
                {historyTools.map(
                  ({ page: destination, label, icon: Icon }) => (
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
                      <Icon size={17} />
                      <span>{label}</span>
                    </button>
                  ),
                )}
              </div>
            </details>
          </nav>
          <div className="workspace-label">
            <span className="profile-initial" aria-hidden="true">
              A
            </span>
            <span>Alex’s history</span>
          </div>
        </aside>
        <div className="workspace">
          <main
            id="main-content"
            className={page === "Home" ? "home-page" : undefined}
            tabIndex={-1}
          >
            <div className="page-header">
              <div>
                <h1>{pageTitle[page]}</h1>
              </div>
              <div className="header-actions">
                <div className="desktop-demo">{demoControl}</div>
                {page !== "Home" && (
                  <button className="primary" onClick={onImport}>
                    <Plus size={18} />
                    {hasDraft ? "Continue review" : "Add records"}
                  </button>
                )}
              </div>
            </div>
            {children}
          </main>
        </div>
      </div>
      {aboutOpen && (
        <Modal title="About this demo" onClose={() => setAboutOpen(false)}>
          <p className="modal-copy">
            This workspace contains invented records for exploring how Modus
            keeps measurements connected to their sources.
          </p>
          <div className="provenance-sections">
            <section>
              <h3>An authored example</h3>
              <p>
                Alex’s starting history was written for this project: three
                documents with nine measurements across 2018, 2021, and 2026. It
                is not a real person’s history and was not generated by Synthea.
                Date filters and reviewed imports change what you see.
              </p>
            </section>
            <section>
              <h3>Separate research data</h3>
              <p>
                The wider project includes histories generated with Synthea for
                research and software development. Those generated histories are
                separate from this authored profile. Prepared training examples
                and evaluation cases are separate development materials; no
                trained Modus model or clinical validation is claimed. No real
                personal health records are used.
              </p>
            </section>
            <section>
              <h3>How documents are read</h3>
              <p>
                Local text extraction runs without a model. Optional Local OCR
                runs the TeleOCR model on this computer. Meta extraction is a
                separate, explicit choice when configured and sends the selected
                document to Meta. Every extracted draft requires your review
                before it is added.
              </p>
            </section>
            <section>
              <h3>What the dates mean</h3>
              <p>
                Starting records use authored availability dates. New records
                become available when your reviewed measurements are saved. A
                measurement date, report issue time, and availability time
                remain separate; unknown report times stay unknown.
              </p>
            </section>
          </div>
          <p className="modal-copy">
            <a href="/LOINC_short_license.txt" target="_blank" rel="noreferrer">
              Terminology license notice
            </a>
          </p>
          <div className="about-footer">
            <span>
              Record review and replay · No health interpretation or advice
            </span>
            <button className="text-button" onClick={() => setAboutOpen(false)}>
              Back to workspace <ArrowUpRight size={14} />
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
