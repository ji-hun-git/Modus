import { ArrowRight, ArrowUpRight, CalendarDays } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact } from "./historyTypes";
import { recordLabel } from "./types";
import { dateLabel } from "./ui";

export default function OverviewRecordLists({
  days,
  undated,
  onInspect,
  onSelect,
  onNavigate,
}: {
  days: { date: string; facts: HistoryFact[] }[];
  undated: HistoryFact[];
  onInspect: (fact: HistoryFact) => void;
  onSelect: (selection: { title: string; facts: HistoryFact[] }) => void;
  onNavigate: (page: Page) => void;
}) {
  return (
    <>
      {days.length > 0 && (
        <section
          className="overview-recent"
          aria-labelledby="overview-recent-title"
        >
          <div className="overview-section-heading">
            <h2 id="overview-recent-title">Recent records</h2>
            <button
              className="text-button"
              onClick={() => onNavigate("Timeline")}
            >
              View timeline <ArrowRight size={14} />
            </button>
          </div>
          <div className="overview-recent-list">
            {days.slice(0, 5).map((day) => {
              const labels = [
                ...new Set(day.facts.map((fact) => recordLabel(fact.label))),
              ];
              return (
                <button
                  type="button"
                  key={day.date}
                  className="overview-recent-record"
                  onClick={() =>
                    onSelect({
                      title: `Records · ${dateLabel(day.date)}`,
                      facts: day.facts,
                    })
                  }
                >
                  <CalendarDays size={18} />
                  <time dateTime={day.date}>{dateLabel(day.date)}</time>
                  <span>
                    <strong>
                      {labels.slice(0, 3).join(", ")}
                      {labels.length > 3 ? ` +${labels.length - 3}` : ""}
                    </strong>
                    <small>
                      {day.facts.length}{" "}
                      {day.facts.length === 1 ? "record" : "records"}
                    </small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              );
            })}
          </div>
        </section>
      )}
      {undated.length > 0 && (
        <section
          className="overview-undated"
          aria-labelledby="overview-undated-title"
        >
          <div className="overview-section-heading">
            <h2 id="overview-undated-title">Dates to check</h2>
            <span>Partial or missing dates</span>
          </div>
          {undated.slice(0, 3).map((fact) => (
            <button
              type="button"
              className="overview-undated-record"
              key={fact.id}
              onClick={() => onInspect(fact)}
            >
              <span>
                <strong>{recordLabel(fact.label)}</strong>
                <small>{fact.occurred_on || "Date not recorded"}</small>
              </span>
              <span>
                View source <ArrowUpRight size={14} />
              </span>
            </button>
          ))}
          {undated.length > 3 && (
            <button
              className="text-button"
              onClick={() =>
                onSelect({
                  title: "Partial or missing dates",
                  facts: undated,
                })
              }
            >
              View all {undated.length} records <ArrowRight size={14} />
            </button>
          )}
        </section>
      )}
    </>
  );
}
