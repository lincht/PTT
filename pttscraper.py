import os
import re
import json
import argparse
import time
from datetime import datetime
from collections import Counter
from progressbar import progressbar
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd


host = 'https://www.ptt.cc'


class PTTPage(object):
    
    def __init__(self, url):
        cookies = {'over18': '1'}
        self.url = url
        while True:
            try:
                r = requests.get(self.url, cookies=cookies)
            except:
                print('\nConnection failed. Retrying.')
                time.sleep(5)
                continue
            # Allow 404 to let empty articles pass,
            # which will fail the integrity test anyway
            if r.status_code in [200, 404]:
                break
        self.text = r.text
        self.soup = BeautifulSoup(self.text, 'lxml')


class IndexPage(PTTPage):
    
    def get_prev_page(self):
        """Return page number of the page before this one."""
        prev_url = self.soup.select('a[class*="btn wide"]')[1]['href']
        return int(re.search(r'index(\d*).html', prev_url).group(1))
    
    def get_articles(self):
        """Return all articles listed on the index page, and push data
        corresponding to each article as two separate DataFrames.
        """
        as_ = self.soup.select('.title a')
        titles = [a.get_text() for a in as_]
        urls = [host+a['href'] for a in as_]
        # Skip announcements and pinned articles, which may have a special format
        to_remove = [i for i, t in enumerate(titles)
                     if re.search('^\[公告\]|置底|^\[協尋\]', t)]
        urls = [u for i, u in enumerate(urls) if i not in to_remove]
        articles = [ArticlePage(u) for u in urls]
        # Keep only intact, non-forward articles
        # Note: If an article is damaged and thus lacks .forward attribute,
        # the predicate expr will still evaluate to False due to short-circuit.
        articles = [a for a in articles if a.integrity and not a.forward]
        
        authors = [a.author for a in articles]
        aliases = [a.alias for a in articles]
        titles = [a.title for a in articles]
        dates = [a.date for a in articles]
        ips = [a.ip for a in articles]
        locs = [a.loc for a in articles]
        cities, countries = tuple(zip(*locs))
        pushes = [a.push_counts for a in articles]
        ups = [p['推'] for p in pushes]
        downs = [p['噓'] for p in pushes]
        comments = [p['→'] for p in pushes]
        urls = [a.url for a in articles]
        # Get push data for each article
        push_data = pd.concat([a.push_data for a in articles if a.push_data is not None])
        articles = pd.DataFrame(dict(author=authors,
                                     alias=aliases,
                                     title=titles,
                                     date=dates,
                                     ip=ips,
                                     city=cities,
                                     country=countries,
                                     ups=ups,
                                     downs=downs,
                                     comments=comments,
                                     url=urls))
        return articles[['author', 'alias', 'title', 'date', 'ip', 'city', 'country',
                         'ups', 'downs', 'comments', 'url']], push_data
    
    def write(self, fname):
        """Write articles and push data to two csv files."""
        articles, push_data = self.get_articles()
        push_fname = fname[:-4] + '_push.csv'
        if not os.path.isfile(fname):
            articles.to_csv(fname, index=False)
            push_data.to_csv(push_fname, index=False)
        else:
            articles.to_csv(fname, mode='a', header=False, index=False)
            push_data.to_csv(push_fname, mode='a', header=False, index=False)


class ArticlePage(PTTPage):
    
    def __init__(self, url):
        super().__init__(url)
        self.integrity = self.check_integrity()
        if self.integrity:
            self.forward = self.is_forward()
            if not self.forward:
                self.author = self.get_author()
                self.alias = self.get_alias()
                self.title = self.get_title()
                self.date = self.get_date()
                self.ip = self.get_ip()
                self.loc = self.get_loc()
                self.push_counts = self.push_counts()
                self.push_data = self.get_push_data()
    
    def check_integrity(self):
        """Check article metadata for integrity."""
        metas = self.soup.select('.article-meta-value')
        board = re.search(r'bbs/(.*?)/', self.url).group(1)
        return len(metas) == 4 and metas[1].text == board

    def is_forward(self):
        """Check if the current article is a forward."""
        spans = self.soup.select('.f2')
        forward = re.search(r'本文轉錄自', spans[0].text)
        if forward:
            return True
        else:
            return False

    def get_author(self):
        text = self.soup.select('.article-meta-value')[0].get_text()
        return re.search(r'([^(]*)', text).group(1).rstrip()
    
    def get_alias(self):
        text = self.soup.select('.article-meta-value')[0].get_text()
        match = re.search(r'\((.*)\)', text)
        if match:
            return match.group(1)
        else:
            # In case someone edited out their alias
            return ''
    
    def get_title(self):
        return self.soup.select('.article-meta-value')[2].get_text()
    
    def get_date(self):
        text = self.soup.select('.article-meta-value')[3].get_text()
        try:
            return datetime.strptime(text, '%a %b %d %H:%M:%S %Y').strftime('%Y-%m-%d %H:%M:%S')
        except:
            # Fix incomplete or missing year
            text = re.match(r'(.*\d{2}:\d{2}:\d{2}).*', text).group(1)
            date = datetime.strptime(text, '%a %b %d %H:%M:%S')
            date = date.replace(year=datetime.now().year)
            return date.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_ip(self):
        spans = self.soup.select('.f2')
        texts = [s.get_text() for s in spans]
        try:
            text = [t for t in texts if re.match(r'※ 發信站: 批踢踢實業坊\(ptt\.cc\), 來自:', t)][0]
            ip = re.search(r'來自: ([0-9.]*)', text).group(1) 
        except:
            # In case someone edited out their ip
            text = [t for t in texts if re.match(r'※ 編輯:', t)][0]
            ip = re.search(r'\(([0-9.]*)\)', text).group(1)
        return ip
    
    def get_loc(self, ip=None):
        if ip is None:
            ip = self.get_ip()
        while True:
            try:
                r = requests.get('http://www.geoplugin.net/json.gp?ip='+ip)
            except:
                print('\nConnection failed. Retrying.')
                time.sleep(5)
                continue
            if r.status_code == 200:
                break
        geo_json = r.text
        try:
            geo_dict = json.loads(geo_json)
        except:
            # Fix countryName for Myanmar, which causes json parser to fail
            burma_regex = r'[\s\[]*Burma[\s\]]*'
            burma = re.search(burma_regex, geo_json)
            if burma:
                geo_json = re.sub(burma_regex, '', geo_json)
                geo_dict = json.loads(geo_json)
        return geo_dict['geoplugin_city'], geo_dict['geoplugin_countryName']
    
    def push_counts(self):
        push_tags = self.soup.select('span[class*="push-tag"]')
        return Counter([t.get_text().rstrip() for t in push_tags])

    def get_push_data(self):
        # More robust to first isolate push contents
        main_content = str(self.soup.select('div#main-content')[0])
        push_soup = BeautifulSoup(
            main_content[main_content.find('<span class="f2">※ 發信站: 批踢踢實業坊(ptt.cc)'):],
            'lxml')
        authors = [s.text for s in push_soup.select('span[class*="f3 hl push-userid"]')]
        # Return None if no push contents
        if not authors:
            return None
        push_map = {'推': 1, '→': 0, '噓': -1}
        pushes = [push_map[s.text[0]] for s in push_soup.select('span[class*="push-tag"]')]
        texts = [s.text[2:] for s in push_soup.select('span[class*="f3 push-content"]')]
        ip_dts = [s.text.strip() for s in push_soup.select('span[class*="push-ipdatetime"]')]
        ips = [re.match(r'\d{,3}[.]{1}\d{,3}[.]{1}\d{,3}[.]{1}\d{,3}', ip_dt).group()
               if re.match(r'\d{,3}[.]{1}\d{,3}[.]{1}\d{,3}[.]{1}\d{,3}', ip_dt) else np.nan
               for ip_dt in ip_dts]
        # Query only once for each unique IP to save time
        unique_ips = set(ips)
        # Handle missing IPs
        unique_locs = [self.get_loc(ip) if type(ip) == str else (np.nan, np.nan)
                       for ip in unique_ips]
        to_loc = {ip: loc for ip, loc in zip(unique_ips, unique_locs)}
        locs = [to_loc[ip] for ip in ips]
        cities, countries = tuple(zip(*locs))
        year = self.soup.select('.article-meta-value')[3].text.split(' ')[4]
        dts = [year+'/'+re.search(r'\d{2}/\d{2} \d{2}:\d{2}', ip_dt).group()+':00'
               if re.search(r'\d{2}/\d{2} \d{2}:\d{2}', ip_dt) else np.nan
               for ip_dt in ip_dts]
        dts = [datetime.strptime(dt, '%Y/%m/%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
               if type(dt) == str else np.nan for dt in dts]
        push_data = pd.DataFrame(dict(url=self.url,
                                      author=authors,
                                      push=pushes,
                                      text=texts,
                                      ip=ips,
                                      city=cities,
                                      country=countries,
                                      dt=dts))
        return push_data[['url', 'author', 'push', 'text', 'ip', 'city', 'country', 'dt']]


def main(board=None, n_pages=None, fname=None):
    """
    Scrape PTT articles.
    Default behavior is to scrape backwards ``n_pages`` pages, starting from the latest one.
    Currently main content of the article is not scraped.
    
    Parameters
    ----------
    board : str
        Board name. If None, default to 'Gossiping'.
    
    n_pages : int
        Number of pages to scrape. If None, default to 50.
    
    fname : str
        Output file name. If None, default to '{board}_{%Y%m%d}.csv', where {%Y%m%d} is current date.
    """
    if board is None:
        board = 'Gossiping'
    if n_pages is None:
        n_pages = 50
    if fname is None:
        ymd = datetime.now().strftime('%Y%m%d')
        fname = board + '_' + ymd + '.csv'
    
    next_to_last = IndexPage(host+'/bbs/'+board+'/index.html').get_prev_page()
    for p in progressbar(list(range(next_to_last-n_pages+2, next_to_last+1)) + ['']):
        start = time.time()
        index_page = IndexPage(host+'/bbs/'+board+'/index'+str(p)+'.html')
        index_page.write(fname)
        end = time.time()
        elapsed = end - start
        # Make sure not to exceed limit of 120 requests/min (10 s/page)
        if elapsed < 10:
            time.sleep(10 - elapsed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', dest='board')
    parser.add_argument('-p', dest='n_pages', type=int)
    parser.add_argument('-f', dest='fname')
    args = parser.parse_args()
    main(args.board, args.n_pages, args.fname)
