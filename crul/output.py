from cgi import escape as html_escape
from textwrap import dedent

from crul import JSONSerialiser


def output_text(crawl):
    for n, page in enumerate(crawl):
        print (
            u'#{n}: {url}\n'
            u'  Title: {title}\n'
            u'  Depth: {depth}\n'
            u'  Links:\n{links}'
            u'  Assets:\n{assets}'
        ).format(
            n=n,
            url=page.url or page.canonical_url,
            title=page.title,
            depth=page.depth,
            links=u''.join(
                u'    - %s\n' % l.href
                for l in page.links or ()
            ),
            assets=u''.join(
                u'    - %s: %s\n' % (a.type, a.href)
                for a in page.assets or ()
            ),
        ).encode('utf-8')


def output_json(crawl):
    serialiser = JSONSerialiser()
    for page in crawl:
        print serialiser.dump_page(page)


def output_sitemap(crawl):
    print dedent('''
        <?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
    ''').strip()
    for page in crawl:
        print '  <url><loc>%s</loc></url>' % html_escape(page.url or page.canonical_url)
    print '</urlset>'
