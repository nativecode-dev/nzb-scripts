import feedparser
import imdb
import re
import time

from datetime import *
from utils import *
from FeedImporter import *
from MovieFeedItem import *

REGEX_IMDB_TITLE=re.compile('.*\s\((\d{4})\)', re.IGNORECASE)
REGEX_IMDB_URL=re.compile('http://www.imdb.com/title/tt(\d+)', re.IGNORECASE)

class MovieFeedImporter(FeedImporter):
    """IMDB client used to access searches."""
    _imdb_client = imdb.IMDb()

    def _parse_feed(self, feed, callback_exists, callback_parsed):
        movie_feed_items = []
        cooldown_counter = 0

        for feed_item in feed['items']:
            try:
                movie_feed_item = self._parse_feed_item(feed_item, callback_exists)

                if movie_feed_item:
                    movie_feed_items.append(movie_feed_item)
                    if callback_parsed: callback_parsed(movie_feed_item)
                    cooldown_counter += 1
            except Exception as e:
                print('Failed to parse feed item due to %s.' % e)
                pass

            if cooldown_counter > FeedImporter._cooldown_max_count:
                cooldown_counter = 0
                print('Cooldown period reached, waiting %s seconds.' % FeedImporter._cooldown_period)
                time.sleep(MovieFeedImporter._cooldown_period)

        return movie_feed_items


    def _parse_feed_item(self, feed_item, callback_exists):
        feed_description = None if not 'description' in feed_item else feed_item['description']
        feed_url = feed_item['link']
        feed_title = feed_item['title']

        if callback_exists and callback_exists(feed_url):
            return None

        guess = self._guess(feed_title)
        feed_title_clean = guess['title']
        feed_year = guess['year']

        feed_imdb_id = self._find_imdb_id(feed_description, feed_title_clean, feed_year)

        movie_feed_item = MovieFeedItem()
        movie_feed_item.description = feed_description
        movie_feed_item.imdb_id = feed_imdb_id
        movie_feed_item.url = feed_url
        movie_feed_item.title = feed_title
        movie_feed_item.title_parsed = feed_title_clean
        movie_feed_item.year = feed_year

        return movie_feed_item


    def _find_imdb_id(self, description, title, year):
        if description:
            match = REGEX_IMDB_URL.match(description)
            if match:
                return int(match.group(1))

        return self._search_imdb_id(title, year)


    def _search_imdb_id(self, title, year):
        movies = Retry(lambda: MovieFeedImporter._imdb_client.search_movie(title))

        for movie in movies:
            title_canonical = movie['long imdb canonical title']
            match = REGEX_IMDB_TITLE.match(title_canonical)
            if match:
                match_year = int(match.group(1))
                # First one to match the year is likely the right one, because
                # it should be sorted by relevance.
                if match_year == year:
                    return int(self._imdb_client.get_imdbID(movie))
