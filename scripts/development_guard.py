"""Run a development command with a read/write tripwire around frozen suites.

This operator check prevents even hashing or statting held-out corpus files.
It is a Python access audit, not a general OS sandbox. Do not use it for holdout.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import runpy
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', choices=('compare_workflows', 'evaluate_heldout_documents', 'compare_development'))
    args, remaining = parser.parse_known_args()
    if '--split' in remaining and remaining[remaining.index('--split') + 1] != 'dev':
        raise ValueError('This guard only permits development execution')
    roots = [os.path.normcase(os.path.abspath(ROOT/'evaluation'/name)) for name in ('workflow_v1','documents_v1')]
    reads, denied = set(), []
    def check(path, writing=False):
        if not isinstance(path, (str, bytes, os.PathLike)):
            return
        absolute = os.path.normcase(os.path.abspath(os.fsdecode(path)))
        for corpus in roots:
            if absolute == corpus or not absolute.startswith(corpus+os.sep):
                continue
            relative = os.path.relpath(absolute, corpus).replace(os.sep,'/')
            permitted = relative in {'dev.json','freeze.json','fixtures','fixtures/dev'} or relative.startswith('fixtures/dev/')
            if not permitted or writing:
                denied.append({'path':relative,'operation':'write' if writing else 'read_or_stat'})
                raise PermissionError('Development guard blocked frozen corpus access')
            reads.add(os.path.relpath(absolute,ROOT).replace(os.sep,'/'))
    def audit(event, values):
        if event == 'open':
            path, mode, flags = values
            writing = (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)))
            check(path,writing)
    original_stat = Path.stat
    def stat(path,*a,**kw):
        check(path)
        return original_stat(path,*a,**kw)
    Path.stat = stat
    sys.addaudithook(audit)
    sys.path.insert(0,str(ROOT/'scripts'))
    sys.argv = [str(ROOT/'scripts'/(args.script+'.py')),*remaining]
    try:
        runpy.run_path(sys.argv[0],run_name='__main__')
    finally:
        folder=ROOT/'evaluation/access-audits'
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]+'.json')
        path.write_text(json.dumps({'script':args.script,'allowed_corpus_paths':sorted(reads),'denied':denied,
            'heldout_access_permitted':False,'limitations':'Python file-open and Path.stat audit; no OS sandbox claim'},indent=2)+'\n',encoding='utf-8')
        print('Development access audit: '+str(path))


if __name__=='__main__':
    main()
