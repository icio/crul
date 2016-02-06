import re
from itertools import chain
from urlparse import urljoin, urlparse

from bs4 import BeautifulSoup

from crul import Page, Link


class PageParser(object):
    def __init__(self, tag_parser=None):
        self.tag_parser = tag_parser or 'lxml'

    def parse(self, resp, depth=0):
        if self.looks_like_html(resp):
            return self.parse_html(resp, depth=depth)
        else:
            return Page(
                url=resp.request.url, canonical_url=resp.request.url,
                headers=resp.headers,
                fetched=True, title=None, no_index=True, links=[], assets=[],
                depth=depth,
            )

    def parse_html(self, resp, depth=0):
        soup = BeautifulSoup(resp.text, self.tag_parser)
        base = self.parse_base(resp, soup)

        return Page(
            url=resp.request.url,
            fetched=True,
            headers=resp.headers,
            canonical_url=self.parse_canonical_url(resp, soup, base),
            title=self.parse_title(resp, soup, base),
            no_index=self.parse_no_index(resp, soup, base),
            links=list(set(self.parse_links(resp, soup, base, depth + 1))),
            assets=list(sorted(set(self.parse_assets(resp, soup, base, depth + 1)))),
            depth=depth,
        )

    def looks_like_html(self, resp):
        return resp.status_code == 200 and 'html' in resp.headers.get('Content-Type', '')

    def parse_base(self, resp, soup):
        try:
            return soup.base['href']
        except (TypeError, AttributeError):
            return resp.url

    def parse_title(self, resp, soup, base):
        try:
            return soup.title.string
        except Exception:
            return None

    def parse_canonical_url(self, resp, soup, base):
        canon = None
        try:
            # From the first `Link: <http://...>; rel="canonical"` header.
            canon = re.search(r'<([^>]+)>;\s*rel="canonical"', resp.headers['link'], re.IGNORECASE).group(1)
            if canon:
                return urljoin(base, canon)
        except (KeyError, AttributeError):
            pass

        try:
            if soup:
                # From the first `<link rel="canonical" href="http://..." />` tag.
                canon = soup.find('link', rel='canonical').href
                if canon:
                    return urljoin(base, canon)
        except Exception:
            pass

        # Assume the requested URL is the canonical URL. Potentially problematic
        # where query-strings do not actually change page content.
        return resp.url

    def parse_no_index(self, resp, soup, base):
        robots_meta = soup and soup.find('meta', attrs={'name': 'robots'})
        return (
            (robots_meta and robots_meta['content'] and 'noindex' in robots_meta['content'].lower()) or
            ('noindex' in resp.headers.get('X-Robots-Tag', ''))
        )

    def parse_links(self, resp, soup, base, depth=1):
        if not soup:
            return

        # Check whether all links are nofollow.
        robots_meta = soup and soup.find('meta', attrs={'name': 'robots'})
        no_follow = (
            (robots_meta and robots_meta['content'] and 'nofollow' in robots_meta['content'].lower()) or
            ('nofollow' in resp.headers.get('X-Robots-Tag', ''))
        )

        # Look for anchor and Link elements.
        local = urlparse(resp.url)
        for anch in soup.find_all('a', href=True):
            href = urlparse(urljoin(base, anch['href']))
            yield Link(
                type='anchor',
                href=href.geturl(),
                no_follow=no_follow or 'rel' in anch and 'nofollow' in anch['rel'],
                external=href.netloc != local.netloc or href.scheme != local.scheme,
                depth=depth,
                referrer=resp.url,
            )

    def parse_assets(self, resp, soup, base, depth=1):
        if not soup:
            return

        local = urlparse(resp.url)

        def link(t, h):
            url = urlparse(h)
            return Link(
                type=t, href=urljoin(base, url.geturl()), no_follow=False,
                referrer=resp.url, depth=depth,
                external=url.netloc != local.netloc or url.scheme != local.scheme,
            )

        for asset in chain(
                soup.find_all('script', src=True),
                soup.find_all('img', src=True),
                soup.find_all('embed', src=True),
                soup.find_all('audio', src=True),
                soup.find_all('video', src=True),
                soup.find_all('iframe', src=True)):
            yield link(asset.name, asset['src'])
        for obj in soup.find_all('object', data=True):
            yield link('object', object['data'])
        for lnk in soup.find_all('link', rel=True, href=True):
            yield link(
                lnk['rel'] if hasattr(lnk['rel'], 'join') else ','.join(lnk['rel']),
                lnk['href']
            )
