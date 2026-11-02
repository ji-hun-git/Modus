import { useEffect, useState } from 'react';
import { api, ApiError } from './api';
import type { HistoryView } from './historyTypes';
import { seriesMatches, type LongitudinalSeries } from './longitudinalSeries';

export default function useLongitudinalSeries(parent:HistoryView, anchorId:string) {
  const [position,setPosition]=useState({identity:'',offset:0});
  const [retry,setRetry]=useState(0);
  const [loaded,setLoaded]=useState<{key:string;series:LongitudinalSeries}|null>(null);
  const [failure,setFailure]=useState<{key:string;message:string;expired:boolean}|null>(null);
  const snapshot=parent.page?.snapshot_id || '';
  const identity=JSON.stringify([snapshot,anchorId,parent.scope]);
  const offset=position.identity===identity?position.offset:0;
  const key=JSON.stringify([identity,offset,retry]);
  useEffect(()=>{
    if (!snapshot) return;
    const controller=new AbortController();
    const query=new URLSearchParams({snapshot_id:snapshot,fact_id:anchorId,offset:String(offset),limit:'30'});
    void api<LongitudinalSeries>(`/history/series?${query}`,{signal:controller.signal}).then(series=>{
      if (controller.signal.aborted) return;
      if (!seriesMatches(series,snapshot,anchorId,parent.scope,offset)) throw new Error('This series does not match the selected record and history view.');
      setLoaded({key,series});
    }).catch((error:Error)=>{
      if (!controller.signal.aborted) setFailure({key,message:error.message,expired:error instanceof ApiError && [409,410].includes(error.status)});
    });
    return ()=>controller.abort();
  },[key]);
  return {series:loaded?.key===key?loaded.series:null,
    error:!snapshot?{message:'Refresh your history before opening this series.',expired:true}:failure?.key===key?failure:null,
    offset,setOffset:(next:number)=>setPosition({identity,offset:next}),retry:()=>setRetry(value=>value+1)};
}
