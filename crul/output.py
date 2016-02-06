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
    raise NotImplementedError()  # TODO: Implement me.


def output_sitemap(crawl):
    raise NotImplementedError()  # TODO: Implement me.


def output_dot(crawl):
    raise NotImplementedError()  # TODO: Implement me.
