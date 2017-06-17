import asyncio
from threading import Thread

async def cr(a):
  print('coroutine 1: %s' % a)

async def cr2():
  print('coroutine 2: calling cr')
  await cr('sto')


def call_in_loop(lp, cr, *args):
  print('Schedulig %s with args=%s'%(cr, args))
  lp.call_soon_threadsafe(cr2())
  
loop = asyncio.get_event_loop()
loop.call_soon(f)

loop.run_forever()
