import "./AnswerScope.css";
import { ArrowRight } from "lucide-react";
import type { Commit, Scope } from "./types";
import { dateLabel, timeLabel } from "./ui";

export default function AnswerScope({
  scope,
  saved,
  onLatest,
}: {
  scope: Scope;
  saved: Commit | null;
  onLatest: () => void;
}) {
  const hasLaterSave =
    saved &&
    !saved.duplicate &&
    Date.parse(saved.available_at) > Date.parse(scope.known_at);
  return (
    <div className="answer-scope">
      <p>
        Measured through {dateLabel(scope.as_of)}
        <br />
        Files available through {timeLabel(scope.known_at)}
      </p>
      {hasLaterSave && (
        <p className="answer-new-record">
          Your latest saved record is outside this answer’s view.
        </p>
      )}
      <button className="text-button" onClick={onLatest}>
        Use latest files <ArrowRight size={14} />
      </button>
    </div>
  );
}
