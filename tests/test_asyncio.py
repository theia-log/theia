import asyncio

async def routine0(s,n):
  print('CRT:',s,':',n)

async def routine(id, n):
  print('TEST[%s] %d'%(id,n))
  if not n:
    return
  n -= 1
  await routine(id, n)
  await routine0(id, n)

loop = asyncio.get_event_loop()
tasks = [
  asyncio.ensure_future(routine('a',5)),
  asyncio.ensure_future(routine('b',8))]
print('muf')
loop.run_until_complete(asyncio.wait(tasks))
print('puf')
loop.close()

