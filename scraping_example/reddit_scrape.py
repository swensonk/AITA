from bs4 import BeautifulSoup
import requests
import re
import time
import os
import glob


def main():
    initial_urls = ["https://reddit.com/r/AmItheAsshole/comments/1iz4o6f/aita_for_insulting_my_husband_for_what_he_said/"]
    result_folder = '../../reddit_scraper_results'
    
    urls = initial_urls
    post_store = PostStore(result_folder)
    url_store_path = result_folder + '/url_results.txt'

    if os.path.exists(url_store_path):
        url_manager = URLManager.from_file(url_store_path)
        urls = url_manager.get_all_urls()
    else:
        url_manager = URLManager('reddit.com', r'/r/AmItheAsshole/comments/\w+/\w+/(?=[?#]|$)', r'/r/AmItheAsshole/.*')
    save_every_min = 5
    last_save_time = time.time()
    while True:
        for u in urls:
            if url_manager.is_matching(u) and not url_manager.was_crawled(u):
                scraper = RedditScraper(u)
                scraper.get_content()
                url_manager.crawl(u, scraper.soup)

                post = scraper.get_post_content()
                if post is not None:
                    post_id = scraper.get_post_id()
                    post_flair = scraper.get_flair()
                    tokenized_post = scraper.tokenize(post)
                    post_store.add(post_id, post_flair, ' '.join(tokenized_post))
                    print(f'Scraped post: "{post_id}", flair: "{post_flair}"')
            else:
                url_manager.crawl(u)

            if time.time() >= last_save_time + save_every_min * 60:
                url_manager.to_file(url_store_path)
                last_save_time = time.time()

        urls = url_manager.get_all_urls()

    return


class PostStore:
    def __init__(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.folder = folder

        file_list = glob.glob(folder + '/post_*.txt')
        key_list = [f.split('/')[-1].split('post_')[-1].split('.')[0] for f in file_list]
        self.key_set = set(key_list)

    def keys(self):
        return list(self.key_set)

    def add(self, id, flair, contents):
        file_name = self.folder + '/post_' + id + '.txt'

        out = [flair, contents]

        with open(file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out))

    def get(self, id):
        file_name = self.folder + '/post_' + id + '.txt'

        with open(file_name, 'r', encoding='utf-8') as f:
            file_lines = [l.strip() for l in f.readlines()]
        file_lines = [l for l in file_lines if file_lines != '']

        flair = file_lines[0]
        contents = '\n'.join(file_lines[1:])
        return flair, contents


class RedditScraper:
    def __init__(self, url):
        self.url = url
        self.soup = None

    def get_content(self):
        error_code = -1
        time_wait = 5
        while error_code != 0:
            error_code = 0
            try:
                response = requests.get(self.url)
                if response.status_code == 429:
                    error_code = 1
                elif response.status_code >= 500 and response.status_code < 600:
                    error_code = 4
            except requests.exceptions.ReadTimeout:
                error_code = 2
            except requests.exceptions.ChunkedEncodingError:
                error_code = 3

            if error_code == 1:
                print(f'WARNING: "Too many requests" error received, waiting {time_wait:.3f} seconds...')
            elif error_code == 2:
                print(f'WARNING: Timeout error detected, waiting {time_wait:.3f} seconds...')
            elif error_code == 3:
                print(f'WARNING: Invalid chunk length error occurred, trying again in {time_wait:.3f} seconds...')
            elif error_code == 4:
                print(f'WARNING: Server error {response.status_code} received, trying again in {time_wait:.3f} seconds...')

            if error_code != 0:
                time.sleep(time_wait)
                time_wait *= 1.5

        if response.status_code == 200:
            self.soup = BeautifulSoup(response.text, "html.parser")
        else:
            raise Exception(f"Failed to get {self.url}, Status Code: {response.status_code}")

    def parse(self, element, class_name, inner_tag="p"):
        if self.soup:
            elements = self.soup.find_all(element, class_=class_name)
            return [" ".join(p.text.strip() for p in elem.find_all(inner_tag)) for elem in elements]
        return None

    def tokenize(self, text_post):
        text_post = text_post.replace("\\ 's", "")
        punctuation = [".", ",", "(", ")"]
        for punctuation_mark in punctuation:
            text_post = text_post.replace(punctuation_mark, "")

        text_post = text_post.lower()
        text_post = text_post.split()

        return text_post

    def get_flair(self, slot_name = "post-flair"):
        slot_element = self.soup.find(attrs={"slot": slot_name})
        return slot_element.get_text(strip=True) if slot_element else None

    def get_post_content(self):
        post_list = self.parse("div", "text-neutral-content")
        return post_list[0] if post_list else None

    def get_post_id(self):
        if self.soup:
            elements = self.soup.find_all("shreddit-post", id=True)
            return elements[0]["id"]
        return None


class DataExtractor:
    def __init__(self, soup):
        self.soup = soup

    def get_titles(self):
        return [title.text.strip() for title in self.soup.find_all("placeholder")]

    def get_links(self):
        return [a["href"] for a in self.soup.find_all("a", href=True)]


class ScraperManager:  # TODO: Merge some stuff from main() into here
    def __init__(self, urls):
        self.urls = urls
        self.results = []

    def scrape_all(self):
        for url in self.urls:
            scraper = RedditScraper(url)
            scraper.get_content()
            extractor = DataExtractor(scraper.soup)
            self.results.append({
                "id": id,
                "url": url,
                "titles": extractor.get_titles(),
                "links": extractor.get_links()
            })


class URLManager:
    def __init__(self, domain, url_regex, all_url_regex=r'.'):
        self.domain = domain
        self.url_regex = url_regex
        self.all_url_regex = all_url_regex
        self.matching_urls = set()
        self.all_urls = set()
        self.crawled_urls = set()

    def strip_domain(self, url):
        if self.domain in url:
            while self.domain in url:
                url = '/'.join(url.split('/')[1:])
            url = '/' + url
        elif '//' in url:
            return None  # Different domain
        return url

    def validate(self, url):
        url = self.strip_domain(url)
        if url is None:
            return None  # Different domain
        regex_match = re.match(self.all_url_regex, url)
        if regex_match is None:
            return None  # Doesn't match all_url_regex
        return url

    def is_matching(self, url):
        url = self.strip_domain(url)
        if url is None:
            return None  # Different domain
        regex_match = re.match(self.url_regex, url)
        return (regex_match is not None)

    def was_crawled(self, url):
        url = self.validate(url)
        if url is None:
            return True  # Technically wasn't, but we won't crawl it anyway
        return (url in self.crawled_urls)

    def crawl(self, url, soup=None):
        url = self.validate(url)
        if url is None:
            return

        if url in self.crawled_urls:
            return
        self.crawled_urls.add(url)

        if soup is None:
            scraper = RedditScraper('https://' + self.domain + url)
            scraper.get_content()
            soup = scraper.soup
        extractor = DataExtractor(soup)
        new_urls = extractor.get_links()

        for new_url in [url] + new_urls:
            new_url_processed = self.validate(new_url)
            if new_url_processed is None:
                continue  # URL we won't scrape
            if new_url_processed not in self.all_urls:
                self.all_urls.add(new_url_processed)
                if self.is_matching(new_url_processed):
                    self.matching_urls.add(new_url_processed)

    def get_matching_urls(self):
        return ['https://' + self.domain + u for u in list(self.matching_urls)]

    def get_all_urls(self):
        return ['https://' + self.domain + u for u in list(self.all_urls)]

    def get_crawled_urls(self):
        return ['https://' + self.domain + u for u in list(self.crawled_urls)]

    def to_file(self, file_name):
        out = ['URL_LIST']
        out.append(self.domain)
        out.append(self.url_regex)
        out.append(self.all_url_regex)

        out.append('MATCHING')
        out += list(self.matching_urls)

        out.append('ALL')
        out += list(self.all_urls)

        out.append('CRAWLED')
        out += list(self.crawled_urls)

        if os.path.exists(file_name):
            os.replace(file_name, file_name + '.bak')
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out))

    def from_file(file_name):
        self = URLManager('', '')

        with open(file_name, 'r', encoding='utf-8') as f:
            file_lines = [l.strip() for l in f.readlines()]
        file_lines = [l for l in file_lines if file_lines != '']

        self.matching_urls = set()
        self.all_urls = set()
        self.crawled_urls = set()

        curr_url_type = ''
        for i, line in enumerate(file_lines):
            if i == 0:
                if line != 'URL_LIST':
                    raise Exception(f'File {file_name} does not look like a saved URLManager')
            elif i == 1:
                self.domain = line
            elif i == 2:
                self.url_regex = line
            elif i == 3:
                self.all_url_regex = line
            elif line == 'MATCHING' or line == 'ALL' or line == 'CRAWLED':
                curr_url_type = line
            elif curr_url_type == 'MATCHING':
                self.matching_urls.add(line)
            elif curr_url_type == 'ALL':
                self.all_urls.add(line)
            elif curr_url_type == 'CRAWLED':
                self.crawled_urls.add(line)

        return self


if __name__ == "__main__":
    main()
