from typing import Dict
from bs4 import BeautifulSoup
from requests import Response


class ScrapedPageInfo:
  def __init__(self, url: str) -> None:
    self.url = url
  def set_soup(self, soup: BeautifulSoup):
    self.soup = soup
  def set_html(self, html: str):
    self.html = html
  def set_json_output(self, json_output: Dict):
    self.json_output = json_output
  def set_response(self, response: Response):
    self.response = response
