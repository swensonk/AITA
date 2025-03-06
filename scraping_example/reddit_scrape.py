from bs4 import BeautifulSoup
import requests


def main():
    urls = ["https://www.reddit.com/r/AmItheAsshole/comments/1iz4o6f/aita_for_insulting_my_husband_for_what_he_said/"]
    scraper = RedditScraper(urls[0])
    scraper.get_content()
    post_flair = scraper.get_flair()
    post = scraper.parse("div", "text-neutral-content")
    tokenized_post = scraper.tokenize(post[0])
    print("Post Flair: ", post_flair)
    print("tokenized post: ", tokenized_post)
    



class RedditScraper:
    def __init__(self, url):
        self.url = url
        self.soup = None

    def get_content(self):
        response = requests.get(self.url)
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


class DataExtractor:
    def __init__(self, soup):
        self.soup = soup

    def get_titles(self):
        return [title.text.strip() for title in self.soup.find_all("placeholder")]

    def get_links(self):
        return [a["href"] for a in self.soup.find_all("a", href=True)]

class ScraperManager:
    def __init__(self, urls):
        self.urls = urls
        self.results = []

    def scrape_all(self):
        for url in self.urls:
            scraper = RedditScraper(url)
            scraper.get_content()
            extractor = DataExtractor(scraper.soup)
            self.results.append({
                "url": url,
                "titles": extractor.get_titles(),
                "links": extractor.get_links()
            })

main()
