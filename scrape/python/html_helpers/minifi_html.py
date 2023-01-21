from bs4 import BeautifulSoup
from bs4 import element

TAG_LINK_STRINGS = [
  'eBay'
]

def is_tag_link(tag: BeautifulSoup):
  if tag.name != 'a' and tag.name != 'button':
    return False
  children = list(tag.children)
  # print(len(list(children)))
  if len(children) != 1:
    return False
  
  # print('yo')

  child = children[0]
  # print(type(child))
  if type(child) != element.NavigableString:
    return False
  
  # print(str(child).strip())
  if str(child).strip() in TAG_LINK_STRINGS:
    return True
  
  return False

def is_useless_tag(tag: BeautifulSoup):
  if is_tag_link(tag):
    return True
  return False

BAD_TEXT = [
  '',
  'Loading'
]
def has_helpful_children(bs: BeautifulSoup):
  any_helpful_children = False
  for child in bs.children:
    if type(child) == element.Comment:
      pass
    elif type(child) == element.NavigableString:
      if not str(child).strip() in BAD_TEXT:
        any_helpful_children = True
    elif type(child) == element.Tag:
      # print(True)
      child_helpful = False
      if not is_useless_tag(child):
        if child.has_attr('wire:initial-data'):
          child_helpful = True
        if child.name == 'img':
          child_helpful = True
        if has_helpful_children(child):
          child_helpful = True

      if child_helpful:
        any_helpful_children = True
      else:
        child.decompose()
              
  return any_helpful_children

# def remove_useless_html(bs: BeautifulSoup):
#     has_helpful_children(bs)
def get_helpful_html(bs: BeautifulSoup):
  main = bs.find('main')
  if main is not None:
      bs = main
  has_helpful_children(bs)
  return bs

def remove_tags_by_name(bs: BeautifulSoup, tag_name):
    for tag in bs.find_all(tag_name):
        tag.decompose()

def remove_census_tab(bs):
    census_tab = bs.find(attrs={'x-show': "census_tab === 'cgc-census'"})
    if census_tab is not None:
        census_tab.decompose()

def remove_useless_html(bs: BeautifulSoup):
    remove_tags_by_name(bs, 'head')
    remove_tags_by_name(bs, 'script')
    remove_census_tab(bs)

def minify_html(html: str):
  bs = BeautifulSoup(html, 'html.parser')
  remove_useless_html(bs)
  bs = get_helpful_html(bs)
  return str(bs)