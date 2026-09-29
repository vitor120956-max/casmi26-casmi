#!/usr/bin/env python3
"""Dois eventos absolutos; nenhum loop de consulta, sleep ou retry."""
import asyncio,datetime as dt,pathlib,subprocess,sys
ROOT=pathlib.Path('/home/user')
EVENTS=[('named-ready-submit',dt.datetime(2026,9,27,1,15,0,tzinfo=dt.timezone.utc),[]),
        ('score-check-once',dt.datetime(2026,9,27,2,30,tzinfo=dt.timezone.utc),['--report'])]
loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
remaining=set()
async def fire(name,args):
 print('EVENT',name,dt.datetime.now(dt.timezone.utc).isoformat(),flush=True)
 with (ROOT/'wave7_afterbuild_actions.log').open('a') as out:
  proc=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'wave7_run.py'),*args,cwd=str(ROOT),stdout=out,stderr=out)
  code=await proc.wait()
 print('EVENT_DONE',name,'exit',code,flush=True)
 remaining.remove(name)
 if not remaining:loop.stop()
now=dt.datetime.now(dt.timezone.utc)
for name,at,args in EVENTS:
 if at<=now:
  print('SKIP_EXPIRED',name,'use wave7_run.py manually within authorized window',flush=True)
  continue
 remaining.add(name)
 loop.call_later((at-now).total_seconds(),lambda n=name,a=args:loop.create_task(fire(n,a)))
 print('ARMED',name,at.isoformat(),'BRT',at.astimezone(dt.timezone(dt.timedelta(hours=-3))).isoformat(),flush=True)
if remaining:loop.run_forever()
loop.close()
