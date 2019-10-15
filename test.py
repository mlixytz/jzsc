import asyncio
import time

async def wait(x):
    await asyncio.sleep(x)
    if x == 5:
        while True:
            continue
    print(x)


async def main():
    task1 = asyncio.create_task(wait(5))
    task2 = asyncio.create_task(wait(2))

    tasks = [task1, task2]
    await asyncio.gather(*tasks)

asyncio.run(main())