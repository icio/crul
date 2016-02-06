import json
from collections import namedtuple


Task = namedtuple('Task', [
    'url', 'depth', 'referrer',
])

Page = namedtuple('Page', [
    'url', 'canonical_url', 'fetched', 'request', 'response',
    'no_index', 'links', 'assets', 'title', 'depth'
])

Link = namedtuple('Link', [
    'type', 'href', 'no_follow', 'external', 'depth', 'referrer',
])


class JSONPageSerialiser(object):
    def load(self, source):
        j = json.loads(source)

    def load_link(self, link):
        pass

    def dump(self, page):
        return json.dumps({
            'url': page.url,
        })

    def dump_link(self, link):
        pass
