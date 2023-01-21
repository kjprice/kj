import enum
import json
from multiprocessing import AuthenticationError
import os
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup

import requests

# from python.http_helpers.authentication import get_authentication_keys
from python.http_helpers.scraped_page_info import ScrapedPageInfo
from python.html_helpers.minifi_html import minify_html
# from python.http_requests.call_proxy_server import call_proxy_server

from python.misc.config import CACHE_DIR, ensure_directory_exists, use_cache

class HttpResponseBadStatusCodeError(Exception):
  message = None
  status_code = None
  url = None
  http_method = None
  def __init__(self, status_code: int, url: str, http_method: str) -> None:
    self.status_code = status_code
    self.url = url
    self.http_method = http_method

    message = 'Unknown error when trying to {} "{}" with status code {}'.format(self.http_method, url, status_code)
    self.message = message

    super().__init__(message)

class CacheDirs(enum.Enum):
  RESPONSE = 'response'
  REQUEST_PAYLOAD = 'payload'
  REQUEST_HEADERS = 'request_headers'

def get_cache_directory_path(self, cache_dir: CacheDirs, filename: str):
  return os.path.join(self.cache_dir, cache_dir.value, filename)

def is_text_json(text: str):  
  return text[0] == '{'

class MethodOveridException(Exception):
  pass

# TODO: Wire in proxy
USE_CACHE = use_cache()
class Scrape_Abstract:
  def __init__(self, url: str, cache_dir: str, http_method: str = 'POST', should_save_cache = True, authentication: Optional[str] = 'gocollect',
  #  use_proxy=True
   ) -> None:
    self.authentication = authentication
    self.cache_dir = os.path.join(CACHE_DIR, cache_dir)
    self.scraped_page_info = ScrapedPageInfo(url)
    self.http_method = http_method
    self.should_save_cache = should_save_cache
    # self.use_proxy = use_proxy
    self.ensure_cache_directories_exist()
    self.scrape()
  def create_cache_filepath(self, cache_dir: CacheDirs):
    filename = self.get_filename()
    return os.path.join(self.cache_dir, cache_dir.value, filename)
  def get_cache_directory_path(self, cache_dir: CacheDirs):
    return os.path.join(self.cache_dir, cache_dir.value)
  def ensure_cache_directories_exist(self):
    if not USE_CACHE:
      return
    for cache_dir in CacheDirs:
      dir_path = self.get_cache_directory_path(cache_dir)
      ensure_directory_exists(dir_path)

  def save_cache(self, cache_dir: CacheDirs, txt: str):
    if not USE_CACHE:
      return
    with open(self.create_cache_filepath(cache_dir), 'w') as f:
      f.write(txt)

  def read_cache(self, cache_dir: CacheDirs):
    with open(self.create_cache_filepath(cache_dir), 'r') as f:
      return f.read()

  def cache_file_exists(self, cache_dir: CacheDirs):
    return os.path.exists(self.create_cache_filepath(cache_dir))

  def try_load_cache_response(self):
    if self.cache_file_exists(CacheDirs.RESPONSE):
      cache_response = self.read_cache(CacheDirs.RESPONSE)
      if 'Server Error' in cache_response:
        path = self.create_cache_filepath(CacheDirs.RESPONSE)
        # print(f'Found error in file: {path}')
        return None
      
      return cache_response

  def save_response_text(self, text):
    if is_text_json(text):
      self.save_cache(CacheDirs.RESPONSE, text)
    else:
      html = minify_html(text)
      self.save_cache(CacheDirs.RESPONSE, html)

  def get_text(self, **kwargs):
    if USE_CACHE:
      cache_response = self.try_load_cache_response()
      if cache_response is not None:
        return cache_response
    
    text = self.fetch_raw(**kwargs)

    self.save_response_text(text)
    if self.should_save_cache:
      self.save_cache(CacheDirs.RESPONSE, text)

    return text
  
  # def get_gocollect_authentication(self):
  #   authentication_keys = get_authentication_keys()
  #   return {
  #     'cookie': 'gcvid=51334804; _ga=GA1.2.1225185884.1658692315; _fbp=fb.1.1658692314672.743471012; __stripe_mid=d31e8e24-ddea-4bd5-9baa-b7ccabb54b659a9c46; prism_1000427358=aa7e0685-e601-404f-9cfe-3bbd95545ea2; _gid=GA1.2.1794487540.1658937451; gcsid=55289525; _gat=1; XSRF-TOKEN={}; gocollectcom_session={}'.format(
  #         authentication_keys.xsrfToken,
  #         authentication_keys.gcollectionSession,
  #     ),
  #     'x-csrf-token': authentication_keys.csrfToken,
  #   }

  # def get_authentication(self):
  #   if self.authentication == 'gocollect':
  #     return self.get_gocollect_authentication()
    
  #   return {}
  
  def request_html(self, headers: dict, payload: dict) -> Tuple[int, str]:
    # if self.use_proxy:
    #   return call_proxy_server(self.http_method, self.scraped_page_info.url, headers, payload)

    response = requests.request(self.http_method, self.scraped_page_info.url, headers=headers, data=payload, timeout=10)
    self.scraped_page_info.set_response(response)

    return response.status_code, response.text

  def fetch_raw(self, **kwargs):
    payload = self.get_payload(**kwargs)

    headers = {
      # **self.get_authentication(),
      'authority': 'gocollect.com',
      'accept': 'text/html, application/xhtml+xml',
      'accept-language': 'en-US,en;q=0.9',
      'cache-control': 'no-cache',
      'content-type': 'application/json',
      'origin': 'https://gocollect.com',
      'pragma': 'no-cache',
      'referer': 'https://gocollect.com/app/comics/series?sortDir=asc&startsWith=&secondaryTypesConfig[comic-age]=Era+Began&wiredSecondaryTypeValues[comic-age]=&page=2',
      'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"macOS"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
      'x-livewire': 'true',
      **self.get_headers(),
    }

    # TODO: Save all sent info in files
    # if payload:
    #   self.save_cache(CacheDirs.REQUEST_PAYLOAD, payload)
    # self.save_cache(CacheDirs.REQUEST_HEADERS, json.dumps(headers))

    status_code, text = self.request_html(headers, payload)

    if status_code == 200:
      return text
    
    if status_code == 419:
      raise AuthenticationError('Please login again')
    
    raise HttpResponseBadStatusCodeError(status_code, self.scraped_page_info.url, self.http_method)

  def get_html(self, json_output: Dict) -> str:
    html = json_output['effects']['html']

    return html
  
  def scrape(self):
    page_text = self.get_text()
    if is_text_json(page_text):
      json_output = json.loads(page_text)
      self.scraped_page_info.set_json_output(json_output)
      html = self.get_html(json_output)
      self.scraped_page_info.set_html(html)
    else:
      html = page_text
      self.scraped_page_info.set_html(html)
    
    if html:
      soup = BeautifulSoup(html, 'html.parser')
      self.scraped_page_info.set_soup(soup)
  
  def get_scraped_page_info(self) -> ScrapedPageInfo:
    return self.scraped_page_info

  def get_payload(self) -> Dict:
    raise MethodOveridException('Method must be overridden')
  def get_headers(self) -> Dict:
    raise MethodOveridException('Method must be overridden')
  def get_filename(self) -> str:
    raise MethodOveridException('Method must be overridden')
