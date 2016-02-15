#!/usr/bin/env python
"""
Crul website scraper.

Examples:

    A human-readable summary of the (rather outdated) pages on my website:

        $ crul http://www.paul-scott.com/

    Record the results of scraping into a file:

        $ crul http://www.paul-scott.com/ --json > me.scrape

    Render a sitemap of what we just scraped:

        $ crul --replay me.scrape --sitemap > sitemap.xml

    Scrape only 3 pages deep with a single worker, leaving 2 seconds between
    each subsequent request to the site, w/o anything under /developer/flash
    or /forum/:

        $ crul -d 3 -w 1 -t 2 https://www.kirupa.com/ \
            -i developer/flash -i forum/

    Ignore robots.txt and grab everything we can, as fast as we can, with 5
    workers, from <url>:

        $ crul --yolo -w 5 <url>

Usage:
    crul (<url> [options] | --replay=<file>)
            [--disallow=<path>]...
            [--dot | --sitemap | --text | --json]
            [-v|-q] [--log-file=<log-file>]
    crul [--help | --version]

Options:
       --sitemap          Output in XML sitemap format.
       --json             Output in JSON format. [default]
       --text             Output in human-readable text format.
    -A --user-agent       The user-agent sent from the client.
                          [default: Crul/1.0 (+https://github.com/icio/crul)]
    -d --depth=<n>        Traverse n pages deep from the starting point.
                          [default: 100]
    -h --help             Print this help.
    -i --disallow=<path>  Ignore/disallow file paths from being scraped.
    -l --log-file=<file>  Log to the given file.
    -q --quiet            Quiet logging.
    -r --replay=<file>    Load responses from a JSON file, instead of scraping.
    -t --delay=<n>        Wait n seconds between requests to the site.
    -v --verbose          Verbose logging.
       --version          Print the version number.
    -w --workers=<n>      Use n worker threads to make requests in parallel.
                          [default: 4]
       --yolo             Don't bother checking robots.txt.
"""
import logging
import re
from urlparse import urljoin

import requests
from docopt import docopt
from requests.exceptions import RequestException

from crul import JSONSerialiser
from crul.output import output_json, output_sitemap, output_text
from crul.parse import PageParser
from crul.scrape import site_crawl
from crul.traverse import DisallowedSet, PageTraverser


def main(args=None):
    if not args:
        args = docopt(__doc__, version='Crul 1.0')

    if not args['--replay'] and not args['<url>']:
        print __doc__.strip('\n')
        return

    # Configure logging.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    log_fmt = logging.Formatter(
        '%(asctime)s %(threadName)s %(name)s %(levelname)s %(message)s'
    )
    if args['--quiet'] and not args['--log-file']:
        logger.addHandler(logging.NullHandler())
    if not args['--quiet']:
        log_out = logging.StreamHandler()
        log_out.setLevel(logging.DEBUG if args['--verbose'] else logging.INFO)
        log_out.setFormatter(log_fmt)
        logger.addHandler(log_out)
    if args['--log-file']:
        log_file = logging.FileHandler(args['--log-file'])
        log_file.setLevel(logging.DEBUG)
        log_file.setFormatter(log_fmt)
        logger.addHandler(log_file)

    # Input.
    if args['<url>']:
        crawl = main_crawl(args)
    else:
        crawl = main_replay(args['--replay'])

    # Output.
    #
    # Originally the plan was to generate a graphic of all of the inter-
    # connected pages, but after playing about with Graphviz for a while I
    # wasn't able to make anything pretty, so I've not included it. This was
    # the motivation for --replay: I was just going to generate equivalent
    # JSON output in gergle and pipe through this program.
    if args['--json']:
        output_json(crawl)
    elif args['--sitemap']:
        output_sitemap(crawl)
    else:
        output_text(crawl)


def main_crawl(args):
    # TODO: Configure connection pooling.
    session = requests.Session()
    session.headers.update({'User-Agent': args['--user-agent']})

    disallowed, delay = (), 0
    if not args['--yolo']:
        try:
            robots_txt = fetch_robots_txt(args['<url>'], session=session)
            disallowed = parse_disallowed(args['--user-agent'], robots_txt)
            delay = parse_crawl_delay(args['--user-agent'], robots_txt)
        except RequestException:
            logging.debug('Unable to collect robots.txt')

    disallowed = DisallowedSet(list(disallowed) + args['--disallow'])
    logging.debug('Disallowed: %s', disallowed)

    if args['--delay'] is not None:
        delay = float(args['--delay'])
    logging.debug('Delay: %.2f', delay)

    return site_crawl(
        session, args['<url>'], int(args['--workers']), delay,
        parser=PageParser(),
        traverser=PageTraverser(
            max_depth=int(args['--depth']),
            disallowed=disallowed,
        )
    )


def main_replay(replay_file):
    serialiser = JSONSerialiser()
    with open(replay_file, 'r') as fh:
        for line in iter(fh):
            yield serialiser.load_page(line)


def fetch_robots_txt(url, session=None):
    """fetch_robots_txt collects robots.txt from the site of the given URL."""
    robots = (session or requests).get(urljoin(url, '/robots.txt'))
    robots.raise_for_status()
    return robots.text


def parse_crawl_delay(agent, txt):
    """parse_crawl_delay reads the Crawl-Delay config from robots.txt.
    TODO: Take the user-agent into consideration.
    """
    try:
        return float(
            re.search(r'^\s*Crawl-Delay:\s*([\d\.]+)', txt, re.I | re.M)
            .group(1)
        )
    except AttributeError:
        return 0


def parse_disallowed(agent, txt):
    try:
        return re.findall(r'^Disallow:\s*(\S+)', txt, re.I | re.M)
    except AttributeError:
        pass


if __name__ == '__main__':
    main()
