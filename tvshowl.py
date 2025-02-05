#!/usr/bin/env python3

import argparse
import feedparser
import re

from collections import defaultdict
from datetime import datetime, timedelta
from functools import reduce
from os import getenv
from time import struct_time
from trello import TrelloClient
from typing import Dict, Iterable, List, NamedTuple


class Episode(NamedTuple):
    show: str
    title: str
    code: str
    links: List[str]


def fetch_episodes(feed_url: str, after_date: struct_time) -> Iterable[Episode]:
    title_parser = re.compile(
        r'^(?P<show>.+)\s(?P<code>\d{1,3}.\d{1,3})\s(?P<title>.+?)(\s\d{3,4}.*)?$'
    )
    feed = feedparser.parse(feed_url, modified=after_date)

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


def merge_namesake_episodes(episodes: Iterable[Episode]) -> Iterable[Episode]:
    def episode_merger(ep1: Episode, ep2: Episode) -> Episode:
        ep1.links.extend(ep2.links)
        return ep1

    episode_groups: Dict[str, List[Episode]] = defaultdict(list)
    for episode in episodes:
        group_key = episode.show + episode.code
        episode_groups[group_key].append(episode)

    for es in episode_groups.values():
        yield reduce(episode_merger, es)


def push_to_trello(episodes: Iterable[Episode], board_id: str, api_key: str, token: str):
    client = TrelloClient(api_key=api_key, token=token)
    board = client.get_board(board_id)
    first_list = board.open_lists()[0]
    existing_cards = {
        c.name for c in board.open_cards(custom_field_items='false')
    }
    for e in episodes:
        card_name = ' – '.join((e.show, e.code, e.title)) if e.title else e.show
        if card_name not in existing_cards:
            card_desc = ', '.join(
                f'[Link {index}]({link})' for index, link in enumerate(e.links, start=1)
            )
            first_list.add_card(
                name=card_name, desc=card_desc, position='bottom'
            )


def main():
    parser = argparse.ArgumentParser(
        description='Turns showRSS episodes to Trello cards.'
    )
    parser.add_argument('--showrss-feed', default=getenv('FEED_URL'), help='showRSS feed URL')
    parser.add_argument('--trello-board', default=getenv('TRELLO_BOARD'), help='Trello board ID')
    parser.add_argument('--trello-key', default=getenv('TRELLO_KEY'), help='Trello API key')
    parser.add_argument('--trello-token', default=getenv('TRELLO_TOKEN'), help='Trello API token')
    args = parser.parse_args()

    day_ago = (datetime.now() - timedelta(days=1)).timetuple()
    episodes = fetch_episodes(args.showrss_feed, day_ago)
    episodes = merge_namesake_episodes(episodes)
    push_to_trello(
        episodes, args.trello_board, args.trello_key, args.trello_token
    )


if __name__ == '__main__':
    main()
