export type TermMapping = {
  concept_id: string;
  medical_name: string;
  display_name: string;
  requested_terms: string[];
  matched_labels?: string[];
  catalog_version: string;
  reference: {publisher: string; title: string; url: string; checked_on: string};
};
export type RetrievalInfo = {status: string; mappings: TermMapping[];
  clarification?: {question: string; choices: {label: string; message: string}[]}};

export function RetrievalFeedback({retrieval, onChoose}: {retrieval?: RetrievalInfo | null; onChoose: (query:string)=>void}) {
  if (!retrieval) return null;
  if (retrieval.clarification) return <div role="status">
    <p>{retrieval.clarification.question}</p>
    <div className="history-question-suggestions">{retrieval.clarification.choices.map(choice =>
      <button className="secondary" key={choice.message} onClick={()=>onChoose(choice.message)}>{choice.label}</button>)}</div>
  </div>;
  return <TerminologyDetails mappings={retrieval.mappings} />;
}

export function referenceUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password &&
      ['medlineplus.gov', 'www.niddk.nih.gov'].includes(url.hostname) && !url.search && !url.hash ? url.href : null;
  } catch { return null; }
}

export default function TerminologyDetails({ mappings }: {mappings?: TermMapping[]}) {
  if (!mappings?.length) return null;
  return <details className="history-answer-trace" aria-label="Medical terminology matches">
    <summary>How I matched your words</summary>
    <p>General terminology references. Your results come from your source records.</p>
    {mappings.map(term => {
      const url = referenceUrl(term.reference.url);
      return <div key={term.concept_id}>
        <p><strong>{term.requested_terms.join(', ')}</strong> → {term.matched_labels?.length
          ? term.matched_labels.join(', ') : term.display_name}</p>
        {url && <a href={url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
          {term.reference.publisher} · {term.reference.title}</a>}
      </div>;
    })}
  </details>;
}
