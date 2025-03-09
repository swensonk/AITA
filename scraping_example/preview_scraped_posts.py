# TODO: This is just for testing, something like this is from where a model can be made

from reddit_scrape import PostStore, RedditScraper


def main():
    store = PostStore('../../reddit_scraper_results')
    for id in store.keys():
        flair, contents = store.get(id)
        print(f'Retrieved post "{id}", flair "{flair}", beginning with "{contents[:25]}"')


if __name__ == "__main__":
    main()
