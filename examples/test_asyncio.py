import asyncio


async def routine0(s, n):
    print('CRT:', s, ':', n)


async def routine(id, n):
    print('TEST[%s] %d' % (id, n))
    if not n:
        return
    n -= 1
    await routine(id, n)
    await routine0(id, n)

loop = asyncio.get_event_loop()

asyncio.run_coroutine_threadsafe(routine('aa', 3), loop)

loop.run_forever()
