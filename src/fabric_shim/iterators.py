# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Status and historical query result iterator implementation class
import asyncio


# https://blog.finxter.com/python-__anext__-and-__aiter__-magic-methods/
class CommonIterator:
    """ Iterate over an asynchronous source. n Iterations."""

    def __init__(self, n):
        self.current = 0
        self.n = n

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(1)
        print(f"get next element {self.current}")
        self.current += 1
        if self.current > self.n:
            raise StopAsyncIteration
        return self.current - 1


async def main():
    async for i in CommonIterator(3):
        print(f"next element {i}")


asyncio.run(main())
