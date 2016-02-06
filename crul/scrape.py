# -*- coding: utf-8 -*-
import logging
import threading
from functools import partial
from Queue import Queue

import requests
import sloq


def site_crawl(session, init_url, num_workers, delay, parser, traverser):
    """
    Args:
        session: A requests.Session HTTP client.
        init_url: The first URL to request on the target site.
        num_workers: The number of HTTP-client workers to spin up.
        delay: The number of seconds between each request to the target site.
        parser: Parses the http response for content, links, etc. (PageParser)
        traverser: The utility for queueing newly discovered links. (PageTraverser)

    Yields:
        Each Page encountered.

    Flow:

                  v site_crawl(init_url)
                  |
    +----------------------------------------------------+      +--- worker_sentinel [thread x 1] ------------+
    |             |                                      | >-------> Wait for all tasks to be completed.      |
    |  +---<  <---+   pending (Task queue)        <---+  |      |                                             |
    |  |                                              |  | <-------* Append kill signals to all queues.       |
    +----------------------------------------------------+      +---------------------------------------------+
       |                                              |            |
    +----+ worker [thread x num_workers] +---------------+         |
    |  |                                              |  |         |
    |  |   + worker_request +---------------------+   |  |         |
    |  |   |                                      |   |  |         |
    |  +-> | page = page_parser(session.get(url)) |   |  |         |
    |      | page_traverser.follow(page)          | >-+  |         |
    |  +-< | return page                          |      |         |
    |  |   |                                      |      |         |
    |  |   +--------------------------------------+      |         |
    |  |                                                 |         |
    +----------------------------------------------------+         |
       |                                                           |
    +----------------------------------------------------+         |
    |  |                                                 |         |
    |  +--->  >---+   completed (Page queue)             | <-------+
    |             |                                      |
    +----------------------------------------------------+
                  |
                  v iter([Page, ...])
    """
    if num_workers < 1:
        raise ValueError('num_workers >= 1')

    logging.info('Starting crawl of %s (delay: %0.2fs)', init_url, delay)

    #: complete is the queue to which results are sent.
    complete = Queue()
    complete_sentinel = {}
    work_sentinel = {}

    #: pending is the pages we have identified that we are interested in.
    if delay:
        pending = SlowQueue(release_tick=delay, max_slam=1,
                            passthru=work_sentinel)
    else:
        pending = Queue()

    #: workfn takes a task description and fetches the remote content,
    #: enqueuing any additional pages we should look at.
    workfn = partial(worker_request, parser.parse,
                     partial(traverser.follow, pending), session)

    # Start the worker threads.
    for w in xrange(num_workers):
        t = threading.Thread(
            name='Worker-%d' % w,
            target=worker,
            args=(workfn, pending, complete, work_sentinel)
        )
        t.daemon = True
        t.start()

    # Queue some work.
    traverser.queue_url(pending, init_url)

    # Start a background thread to add completion markers to the
    # pending/complete queues when all pending tasks are complete.
    t = threading.Thread(
        name='Worker-Sentinel',
        target=worker_sentinel,
        args=(pending, complete, work_sentinel, num_workers, complete_sentinel)
    )
    t.daemon = True
    t.start()

    # Return an iterator over the complete items.
    for result in iter(complete.get, complete_sentinel):
        if isinstance(result, Exception):
            # Forward exceptions from worker threads to the main thread.
            raise result
        else:
            yield result


def worker_sentinel(pending, complete, worker_sentinel, num_workers,
                    complete_sentinel=None):
    logging.debug('Awaiting all work to complete.')
    pending.join()

    logging.debug('Sending kill signals.')
    for _ in xrange(num_workers):
        pending.put(worker_sentinel)

    complete.put(complete_sentinel)
    logging.debug('Kill signals sent.')


def worker(workfn, in_queue, out_deque, kill_signal):
    logging.debug('Worker started.')
    while True:
        task = in_queue.get()
        if task is kill_signal:
            in_queue.task_done()
            break
        try:
            out_deque.put(workfn(task))
        except Exception as e:
            logging.exception('Worker errored whilst processing %r', task)
            out_deque.put(e)
            break
        finally:
            in_queue.task_done()
    logging.debug('Worker stopped.')


def worker_request(parser, follow_links, session, task):
    headers = {}
    if task.referrer:
        headers['Referrer'] = task.referrer
    for _ in xrange(2):
        try:
            page = parser(session.get(task.url, headers=headers), depth=task.depth)
            break
        except requests.exceptions.ConnectionError:
            # FIXME: There's a peculiar, intermittent ConnectionError being
            # thrown. It only seems to occur when the delay between requests
            # is between 0 and 0.5 seconds -- but doesn't happen and not when
            # there is no delay at all. (╯°□°）╯︵ ┻━┻
            logging.exception('ConnectionError encountered. Retrying...')
    follow_links(page)
    return page


class SlowQueue(sloq.SlowQueue):
    """SlowQueue overrides the default behaviour of sloq.SlowQueue when taking
    an item off of the queue: if the item to be returned is a pass-through
    value, i.e. a kill signal, then we give the value immediately to expedite
    thread-killing at the end of the program.
    """
    def __init__(self, passthru=None, *args, **kwargs):
        self.passthru = passthru
        super(SlowQueue, self).__init__(*args, **kwargs)

    def get(self, block=True, timeout=0):
        if not block or timeout != 0:
            raise ValueError(
                "SlowQueue works only with block=True and timeout=0"
            )
        item = self.queue.get(block=True)
        if item is not self.passthru:
            self.token_bucket.take(block=True)
        return item
