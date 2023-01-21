import re

from python.http_helpers.scrape_abstract import Scrape_Abstract

# import argparse

# parser = argparse.ArgumentParser(prog='Scrape From URL', description='Scrapes content from given url in a json format')
# parser.add_argument('url')

class ScrapePage(Scrape_Abstract):
  page = None
  results_per_page = None
  def __init__(self, url: str) -> None:
    url = url

    super().__init__(url, 'the_donald', http_method='GET', authentication=None)
  def get_payload(self):
    pass

  def get_headers(self):
    return {}
  def get_filename(self):
    return 'donald'

def replace_src_set(html: str) -> str:
  pass


if __name__ == "__main__":
  ROOT_URL = 'https://en.wikipedia.org'
  scrape = ScrapePage('https://en.wikipedia.org/wiki/Donald_Trump')
  html = scrape.get_scraped_page_info().html \
    .replace('href="//', 'href="/') \
    .replace('href="/', 'href="' + ROOT_URL + '/') \
    .replace('src="//', 'src="https://') \
    .replace('src="/', 'src="' + ROOT_URL + '/')
  with open('Donald_Trump.html', 'w') as f:
    f.write(html)