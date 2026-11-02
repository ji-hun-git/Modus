import { useState } from 'react';
import { ArrowUp } from 'lucide-react';
import type { HistoryView } from './historyTypes';
import HistoryQuestionPanel from './HistoryQuestionPanel';
import { Modal } from './ui';

export default function HomeAskBar({view}:{view:HistoryView}) {
  const [question,setQuestion]=useState('');
  const [submitted,setSubmitted]=useState<string|null>(null);
  return <>
    <form className="home-ask-bar" onSubmit={event=>{event.preventDefault();if(question.trim())setSubmitted(question.trim());}}>
      <label htmlFor="home-history-question">Ask about your medical history</label>
      <div><input id="home-history-question" name="history-question" autoComplete="off" maxLength={2000}
        placeholder="When was my last blood pressure reading?" value={question} onChange={event=>setQuestion(event.target.value)} />
        <button type="submit" aria-label="Ask your history"><ArrowUp size={20} aria-hidden="true" /></button></div>
    </form>
    {submitted && <Modal title="Your question, your records" onClose={()=>setSubmitted(null)} wide>
      <HistoryQuestionPanel view={view} initialQuestion={submitted} />
    </Modal>}
  </>;
}
