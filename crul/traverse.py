import logging
from fnmatch import fnmatch
from urlparse import urlparse

from crul import Task


def trim_fragment(url):
    try:
        return url[:url.index('#')]
    except ValueError:
        return url


class DisallowedSet(object):
    def __init__(self, patterns=()):
        self.patterns = ['%s*' % p.lstrip('/') for p in patterns]

    def __contains__(self, path):
        path = path.lstrip('/')
        for pattern in self.patterns:
            if fnmatch(path, pattern):
                return True  # One of the patterns disallows this url.
        return False


class PageTraverser(object):
    def __init__(self, max_depth=100, disallowed=()):
        self.max_depth = max_depth
        self.disallowed = disallowed
        self.seen = set()  # TODO: Is set.{add,__contains__} thread-safe?
        self.allow_external = False
        self.ignore_suffixes = (
            '.png', '.svg', '.pdf', '.jpg', '.gif', '.jpeg', '.mp4', '.wav',
        )

    def sanitize(self, url):
        # Trimming the trailing slash is dubious. Technically they are
        # different URLs...
        return trim_fragment(url).rstrip('/')

    def queue_url(self, pending, url, depth=0, referrer=None):
        sanurl = self.sanitize(url)
        if sanurl in self.seen:
            logging.debug('Skipping %s from %s: link already queued.',
                          url, referrer or 'None')
            return

        logging.debug('Queueing %s from %s', url, referrer or None)
        self.seen.add(sanurl)
        pending.put(Task(
            url=url,
            depth=depth,
            referrer=referrer,
        ))

    def follow(self, pending, page):
        if page.canonical_url:
            self.seen.add(self.sanitize(page.canonical_url))

        for link in page.links:
            url = urlparse(link.href)
            if url.scheme.lower() not in ('http', 'https'):
                logging.debug(
                    'Skipping %s from %s: only following http[s] links.',
                    link.href, link.referrer)
                continue
            if link.no_follow:
                logging.debug('Skipping %s from %s: link marked nofollow.',
                              link.href, link.referrer)
                continue
            if not self.allow_external and link.external:
                logging.debug(
                    'Skipping %s from %s: not following external link.',
                    link.href, link.referrer)
                continue
            if link.depth > self.max_depth:
                logging.debug('Skipping %s from %s: beyond maximum depth.',
                              link.href, link.referrer)
                continue
            if any(url.path.lower().endswith(s) for s in self.ignore_suffixes):
                logging.debug('Skipping %s from %s: ignored suffix.',
                              link.href, link.referrer)
                continue
            if url.path in self.disallowed:
                logging.debug('Skipping %s from %s: disallowed.',
                              link.href, link.referrer)
                continue

            self.queue_url(pending, url=link.href, depth=link.depth,
                           referrer=link.referrer)
