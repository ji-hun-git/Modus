import assert from 'node:assert/strict';
import { test, afterEach } from 'node:test';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source=await readFile(new URL('../src/api.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {localRequest,post,api,acceptLocalSession,clearLocalAccess,hasLocalAccess,lockLocalAccess,readAccessFile}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
const session=(letter='x')=>({access_token:'modus_session_'+letter.repeat(43),idle_seconds:1800,expires_in:28800});
afterEach(()=>clearLocalAccess());

test('writes and binary exports use the same explicit same-origin boundary',async(t)=>{
  const requests=[];
  acceptLocalSession(session());
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
    assert.equal(options.credentials,'omit');
    assert.equal(options.headers.get('Authorization'),'Bearer '+session().access_token);
    assert.equal(options.redirect,'error');
  }
  assert.equal(requests[0].options.headers.get('Content-Type'),'application/json');
  assert.equal(requests[2].options.headers.get('Content-Type'),null);
  assert.equal(requests[2].options.body,form);
});

test('original downloads carry authentication in a header, never their URL',async(t)=>{
  acceptLocalSession(session());
  t.mock.method(globalThis,'fetch',async(path,options)=>{
    assert.equal(path,'/api/history/sources/one/original?known_at=2026-11-03');
    assert.equal(options.headers.get('Authorization'),'Bearer '+session().access_token);
    return new Response('original');
  });
  assert.equal(await (await localRequest('/api/history/sources/one/original?known_at=2026-11-03')).text(),'original');
});

test('unauthorized responses clear the current session and stale responses cannot relock a new one',async(t)=>{
  acceptLocalSession(session());
  t.mock.method(globalThis,'fetch',async()=>new Response('{}',{status:401}));
  await localRequest('/api/history/view');
  assert.equal(hasLocalAccess(),false);
  let finish;
  t.mock.method(globalThis,'fetch',()=>new Promise(resolve=>{finish=resolve;}));
  acceptLocalSession(session('a'));
  const old=localRequest('/api/history/view');
  acceptLocalSession(session('b'));
  finish(new Response('{}',{status:401}));
  await assert.rejects(old,error=>error.status===401);
  assert.equal(hasLocalAccess(),true);
});

test('a deferred private response is discarded after locking',async(t)=>{
  let finish;
  acceptLocalSession(session());
  t.mock.method(globalThis,'fetch',()=>new Promise(resolve=>{finish=resolve;}));
  const pending=localRequest('/api/history/view');
  clearLocalAccess();finish(new Response('private history'));
  await assert.rejects(pending,error=>error.status===401);
});

test('locking clears this window before receiving a server receipt',async(t)=>{
  let finish;
  acceptLocalSession(session());
  t.mock.method(globalThis,'fetch',(path,options)=>{
    assert.equal(path,'/api/access/lock');
    assert.equal(options.headers.get('Authorization'),'Bearer '+session().access_token);
    return new Promise(resolve=>{finish=resolve;});
  });
  const pending=lockLocalAccess();
  assert.equal(hasLocalAccess(),false);
  finish(new Response('{"locked":true}',{status:200}));
  await pending;
});

test('a failed server lock is reported while this window remains locked',async(t)=>{
  acceptLocalSession(session());
  t.mock.method(globalThis,'fetch',async()=>new Response('{}',{status:500}));
  await assert.rejects(lockLocalAccess(),error=>error.status===500);
  assert.equal(hasLocalAccess(),false);
});

test('access files must match this exact window before any credential can be sent',()=>{
  const file={format:'modus-local-access-v1',origin:'http://127.0.0.1:8034',token:'modus_local_'+'x'.repeat(43)};
  assert.equal(readAccessFile(JSON.stringify(file),file.origin),file.token);
  for(const origin of ['http://127.0.0.1:8035','http://localhost:8034','https://untrusted.invalid'])
    assert.throws(()=>readAccessFile(JSON.stringify(file),origin),/current access file/);
  assert.throws(()=>readAccessFile('secret private text',file.origin),/access file/);
});

test('session use never reads or writes browser storage and cleared tokens are not sent',async(t)=>{
  for(const name of ['localStorage','sessionStorage']){
    const descriptor=Object.getOwnPropertyDescriptor(globalThis,name);
    Object.defineProperty(globalThis,name,{configurable:true,get(){throw new Error('storage forbidden');}});
    t.after(()=>{if(descriptor)Object.defineProperty(globalThis,name,descriptor);else delete globalThis[name];});
  }
  acceptLocalSession(session());clearLocalAccess();
  t.mock.method(globalThis,'fetch',async(path,options)=>{
    assert.equal(options.headers.get('Authorization'),null);
    assert.equal(options.credentials,'omit');
    return new Response('{}');
  });
  await localRequest('/api/access/status',{headers:{Authorization:'Bearer discarded'}});
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
