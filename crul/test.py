import unittest

import responses
import requests

from crul.__main__ import fetch_robots_txt, parse_crawl_delay
from crul.traverse import DisallowedSet, trim_fragment


class FetchRobotsTxtTest(unittest.TestCase):
    @responses.activate
    def test_fail(self):
        responses.add(responses.GET, 'http://google.com/robots.txt', status=404)
        with self.assertRaises(requests.exceptions.RequestException):
            fetch_robots_txt('http://google.com/test.html')

    @responses.activate
    def test_succeed(self):
        responses.add(responses.GET, 'http://google.com/robots.txt', status=200,
                      body='Disallow: /failure')
        self.assertEqual(
            fetch_robots_txt('http://google.com/test.html'),
            'Disallow: /failure'
        )


class ParseCrawlDelayTest(unittest.TestCase):
    def test_missing(self):
        self.assertEqual(parse_crawl_delay(None, """
            User-agent: *
            Disallow: /private
            Disallow: /random
        """), 0)

    def test_int(self):
        self.assertEqual(parse_crawl_delay(None, """
            User-agent: *
            Disallow: /private
            Disallow: /random
            Disallow: /day
            Crawl-delay: 1
        """), 1)

    def test_float(self):
        self.assertEqual(parse_crawl_delay(None, 'Crawl-delay: 1.5'), 1.5)

    def test_negative(self):
        self.assertEqual(parse_crawl_delay(None, 'Crawl-delay: -1.5'), 0)

    def test_alpha(self):
        self.assertEqual(parse_crawl_delay(None, 'Crawl-delay: 1.5sdf'), 1.5)
        self.assertEqual(parse_crawl_delay(None, 'Crawl-delay: sdf'), 0)


class DisallowedSetTest(unittest.TestCase):
    def test_empty(self):
        d = DisallowedSet()
        self.assertFalse('/' in d)
        self.assertFalse('/test' in d)

    def test_path(self):
        d = DisallowedSet(['/private'])
        self.assertTrue('/private' in d)
        self.assertTrue('/private-files' in d)
        self.assertTrue('/private/calendar' in d)
        self.assertTrue('private' in d)


class TestTrimFragment(unittest.TestCase):
    def test_fragless(self):
        self.assertEqual(
            trim_fragment('https://hello/world'),
            'https://hello/world'
        )

    def test_trim(self):
        self.assertEqual(
            trim_fragment('https://hello/frag#top'),
            'https://hello/frag'
        )

    def test_multiple(self):
        self.assertEqual(
            trim_fragment('https://hello/frag#top#of#the#morning'),
            'https://hello/frag'
        )


if __name__ == '__main__':
    unittest.main()
