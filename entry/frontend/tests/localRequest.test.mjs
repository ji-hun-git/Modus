import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source=await readFile(new URL('../src/api.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {localRequest,post,api}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));

test('writes and binary exports use the same explicit same-origin boundary',async(t)=>{
  const requests=[];
  t.mock.method(globalThis,'fetch',async(path,options)=>{
    requests.push({path,options});
    return new Response(JSON.stringify({saved:true}),{status:200});
  });
  assert.deepEqual(await post('/history/commit',{reviewed:true}),{saved:true});
  await localRequest('/api/briefs/export',{method:'POST',body:'{}'});
  const form=new FormData();form.set('synthetic_confirmed','true');
  await localRequest('/api/imports/preview',{method:'POST',body:form});
  for(const {options} of requests){
    assert.equal(options.headers.get('X-Modus-Request'),'1');
    assert.equal(options.cache,'no-store');
    assert.equal(options.referrerPolicy,'no-referrer');
    assert.equal(options.credentials,'same-origin');
    assert.equal(options.redirect,'error');
  }
  assert.equal(requests[0].options.headers.get('Content-Type'),'application/json');
  assert.equal(requests[2].options.headers.get('Content-Type'),null);
  assert.equal(requests[2].options.body,form);
});

test('external URLs never receive a request or its body',t=>{
  const fetch=t.mock.method(globalThis,'fetch',()=>{throw new Error('must not send');});
  for(const path of ['https://untrusted.invalid/api/', '//untrusted.invalid/api/', '/api\\untrusted', 'api/history'])
    assert.throws(()=>localRequest(path,{method:'POST',body:'private'}),/local record endpoint/);
  assert.equal(fetch.mock.callCount(),0);
});

test('read errors retain a safe status without echoing validation input',async(t)=>{
  t.mock.method(globalThis,'fetch',async()=>new Response(JSON.stringify({detail:[{type:'validation_error',input:'PRIVATE_CANARY'}]}),{status:422}));
  await assert.rejects(api('/history/view'),error=>error.status===422 && !error.message.includes('PRIVATE_CANARY'));
});
