import json
from collections import namedtuple

from requests.structures import CaseInsensitiveDict


Task = namedtuple('Task', [
    'url', 'depth', 'referrer',
])

Page = namedtuple('Page', [
    'url', 'canonical_url', 'fetched', 'headers', 'no_index', 'links',
    'assets', 'title', 'depth'
])

Link = namedtuple('Link', [
    'type', 'href', 'no_follow', 'external', 'depth', 'referrer',
])


class JSONSerialiser(object):
    def load_page(self, source):
        return self.dict_to_page(json.loads(source))

    def dump_page(self, page):
        return json.dumps(self.page_to_dict(page))

    def dict_to_page(self, p):
        links = [self.dict_to_link(l) for l in p.pop('links', ())]
        assets = [self.dict_to_link(l) for l in p.pop('assets', ())]
        headers = CaseInsensitiveDict(p.pop('headers', {}))
        return Page(links=links, assets=assets, headers=headers, **p)

    def page_to_dict(self, page):
        return dict(page.__dict__.items() + [
            ('headers', dict(page.headers.items())),
            ('links', [self.link_to_dict(l) for l in page.links]),
            ('assets', [self.link_to_dict(l) for l in page.assets]),
        ])

    def dict_to_link(self, link):
        return Link(**link)

    def link_to_dict(self, link):
        return dict(link.__dict__)
