# logging.py

# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import logging.config
import logging.handlers

try:
    # Python 3.7 and newer, fast reentrant implementation
    # without task tracking (not needed for that when logging)
    from queue import SimpleQueue as Queue
except ImportError:
    from queue import Queue
from typing import List

LOGGER = logging.getLogger("asyncio")


class LocalQueueHandler(logging.handlers.QueueHandler):
    """
    Network logging can block the event loop. It is recommended to use a separate thread for handling logs or use
    non-blocking IO.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Removed the call to self.prepare(), handle task cancellation
        try:
            self.enqueue(record)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.handleError(record)


def setup_logging_queue() -> List[logging.Handler]:
    """Move log handlers to a separate thread.

    Replace handlers on the root logger with a LocalQueueHandler,
    and start a logging.QueueListener holding the original
    handlers.

    """
    queue = Queue()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

    handlers: List[logging.Handler] = []

    handler = LocalQueueHandler(queue)
    LOGGER.addHandler(handler)
    for h in LOGGER.handlers[:]:
        if h is not handler:
            LOGGER.removeHandler(h)
            handlers.append(h)

    listener = logging.handlers.QueueListener(
        queue, *handlers, respect_handler_level=True
    )
    # Keep a global reference to the listener so it is not garbage collected
    global _QUEUE_LISTENER
    _QUEUE_LISTENER = listener
    listener.start()


setup_logging_queue()
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
