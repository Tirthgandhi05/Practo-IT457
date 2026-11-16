"""Public endpoint tests, without AWS credentials. Cold starts triggered manually in console."""
import argparse
import csv
import json
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
import requests

p=argparse.ArgumentParser()
p.add_argument('--api',required=True)
p.add_argument('--cold',type=int,default=15)
p.add_argument('--warm',type=int,default=200)
p.add_argument('--levels',default='1,5,10,25,50')
p.add_argument('--memory',type=int,default=256,help='Actual configured memory; read it from Lambda console')
a=p.parse_args()
if a.cold<0 or a.warm<0:p.error('Counts must be nonnegative')
levels=[int(x) for x in a.levels.split(',')] if a.levels else []
if any(n<1 or n>100 for n in levels):p.error('Burst levels must be between 1 and 100')
api=a.api.rstrip('/')
run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
f=Path('results')/(run+'-public');f.mkdir(parents=True)
slot=(datetime.now(timezone.utc)+timedelta(days=30)).replace(hour=10,minute=0,second=0,microsecond=0).isoformat()
fields=['run_id','phase','memory_mb','burst_size','origin','status','client_ms','handler_ms','cold_start','request_id','environment_id','error']
rows=[]

def call(phase,client=None,doctor=None,n=1):
    own=client is None;client=client or requests.Session()
    row=dict.fromkeys(fields,'');row.update(run_id=run,phase=phase,memory_mb=a.memory,burst_size=n,origin='laptop')
    start=time.perf_counter()
    try:
        r=client.post(api+'/book',json={'patient':'Synthetic Test','doctor':doctor or 'test-'+uuid.uuid4().hex,'slot':slot},timeout=25)
        row.update(status=r.status_code,client_ms=round((time.perf_counter()-start)*1000,3))
        try:j=r.json()
        except ValueError:j={}
        for k in ['handler_ms','cold_start','request_id','environment_id']:row[k]=j.get(k,'')
        row['error']=j.get('error',j.get('message',''))
    except requests.RequestException as e:row.update(status=0,client_ms=round((time.perf_counter()-start)*1000,3),error=str(e))
    finally:
        if own:client.close()
    return row

def save(new):
    path=f/'requests.csv';fresh=not path.exists()
    with path.open('a',newline='') as out:
        w=csv.DictWriter(out,fieldnames=fields)
        if fresh:w.writeheader()
        w.writerows(new)
    rows.extend(new)

def parallel(phase,n,doctor=None):
    gate=Barrier(n)
    def fire(i):
        gate.wait(timeout=30)
        return call(phase,doctor=doctor,n=n)
    with ThreadPoolExecutor(max_workers=n) as pool:return list(pool.map(fire,range(n)))

(f/'metadata.json').write_text(json.dumps({'api':api,'run_id':run,'arguments':vars(a),
    'origin':'laptop','cold_method':'manual console environment update; observed label checked',
    'burst_method':'warm-state burst; no reset before burst levels','started_at':datetime.now(timezone.utc).isoformat()},indent=2))
print('Results:',f,flush=True)
print('Close the demo page. Ask teammates not to call or change this Lambda during tests.')
d='check-'+uuid.uuid4().hex
check=[call('first',doctor=d),call('duplicate',doctor=d)];save(check)
if [r['status'] for r in check]!=[201,409]:
    raise SystemExit('STOP: expected 201 then 409, got '+str([(r['status'],r['error']) for r in check]))
print('Basic correctness PASS: 201 then 409.')
race=parallel('same-slot-race',5,'race-'+uuid.uuid4().hex);save(race)
c=Counter(r['status'] for r in race);print('Five-way same-slot race:',dict(c))
print('Race PASS' if c[201]==1 and c[409]==4 else 'Race INCONCLUSIVE/FAILED: inspect statuses; do not report PASS.')
with requests.Session() as client:
    for i in range(a.cold):
        marker=run+'-'+str(i+1)
        print('\nCOLD SAMPLE',i+1,'/',a.cold)
        print('Lambda it457-practo-booking > Configuration > Environment variables > Edit')
        print('Change ONLY COLD_MARKER to:',marker)
        print('Keep TABLE_NAME unchanged. Save and wait until the update succeeds.')
        input('Then press Enter HERE to send ONE request (do not use the Lambda Test button): ')
        row=call('cold-candidate',client=client);save([row])
        print('HTTP',row['status'],'cold_start=',row['cold_start'],'client_ms=',row['client_ms'])
        if row['status']!=201 or row['cold_start'] is not True:
            print('This is NOT a successful cold sample; retained in raw data and classified by observed label.')
    print('\nRunning warmup and',a.warm,'warm-sequence requests...',flush=True)
    save([call('warmup',client=client)])
    for i in range(a.warm):
        save([call('warm-sequence',client=client)])
        if (i+1)%50==0:print(i+1,'/',a.warm,flush=True)
print('\nRunning warm-state bursts. No configuration reset between levels.',flush=True)
for n in levels:
    time.sleep(3)
    batch=parallel('burst',n);save(batch)
    print('Burst',n,'statuses',dict(Counter(r['status'] for r in batch)),
        'cold',sum(r['cold_start'] is True for r in batch),
        'environments',len({r['environment_id'] for r in batch if r['environment_id']}),flush=True)
print('\nDONE. Results:',f)
print('All statuses:',dict(Counter(r['status'] for r in rows)))
print('Successful observed cold candidates:',sum(r['phase']=='cold-candidate' and r['status']==201 and r['cold_start'] is True for r in rows))
print('Analyze: py analyze.py "'+str(f)+'"')
print('Export CloudWatch logs separately. Restore COLD_MARKER to initial after all tests finish.')
