#!/usr/bin/env python

import re

import feedparser

from collections import defaultdict, namedtuple
from datetime import datetime, timedelta

from six import itervalues
from six.moves import reduce
from trello import TrelloClient


SHOWRSS_FEED_URL = '<showrss feed url>'
TRELLO_API_KEY = '<trello api key>'
TRELLO_TOKEN = '<trello token>'
TRELLO_BOARD_ID = '<trello board id>'

Episode = namedtuple('Episode', 'show title code links')


def fetch_episodes(after_date):
    title_parser = re.compile(
        '^(?P<show>.+)\s(?P<code>\d{1,3}.\d{1,3})\s(?P<title>.+?)(\s\d{3,4}.*)?$'
    )
    feed = feedparser.parse(SHOWRSS_FEED_URL, modified=after_date)

    for entry in feed.entries:
        if entry.published_parsed >= after_date:
            parsed_title = title_parser.match(entry.title)
            if parsed_title:
                yield Episode(
                    show=parsed_title['show'],
                    title=parsed_title['title'],
                    code=parsed_title['code'],
                    links=[entry.link]
                )
            else:
                yield Episode(
                    show=entry.title,
                    title='',
                    code='',
                    links=[entry.link]
                )


def merge_namesake_episodes(episodes):
    def episode_merger(ep1, ep2):
        ep1.links.extend(ep2.links)
        return ep1

    episode_groups = defaultdict(list)
    for episode in episodes:
        group_key = episode.show + episode.code
        episode_groups[group_key].append(episode)

    for es in itervalues(episode_groups):
        yield reduce(episode_merger, es)


def push_to_trello(episodes):
    client = TrelloClient(
        api_key=TRELLO_API_KEY,
        token=TRELLO_TOKEN
    )
    board = client.get_board(TRELLO_BOARD_ID)
    list = board.open_lists()[0]
    for e in episodes:
        card_name = ' - '.join((e.show, e.code, e.title)) if e.title else e.show
        card_desc = ', '.join(
            '[Link %d](%s)' % link for link in enumerate(e.links, start=1)
        )
        list.add_card(name=card_name, desc=card_desc, position='bottom')


def main():
    day_ago = (datetime.now() - timedelta(days=1)).timetuple()
    episodes = fetch_episodes(day_ago)
    episodes = merge_namesake_episodes(episodes)
    push_to_trello(episodes)


if __name__ == '__main__':
    main()
