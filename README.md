# Crul :see_no_evil: :hear_no_evil: :speak_no_evil: 

## Installation

```bash
# Prepare a virtual environment (optional)
virtualenv env
. env/bin/activate

# Install crul
pip install git+git://github.com/icio/crul@0.0.1\#egg=crul
```

## Usage

```text
$ crul
Crul website scraper.

Examples:

    A human-readable summary of the (rather outdated) pages on my website:

        $ crul --text http://www.paul-scott.com/

    Record the results of scraping into a file:

        $ crul http://www.paul-scott.com/ > me.scrape

    Render a graph, and a sitemap of what we just scraped:

        $ crul --replay me.scrape --dot | dot -Tpng > me.png
        $ crul --replay me.scrape --sitemap > me.xml

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
       --dot              Output in dot format.
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
```

## Implementation

`crul` is implemented as a threaded set of workers processing a queue of URLs (`crul.scrape.site_crawl`). When new pages have been collected the linked pages (`crul.parse.PageParser`) are appended to the queue (`crul.traverse.PageTraverser`) for the workers to continue processing.

```text
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
```
