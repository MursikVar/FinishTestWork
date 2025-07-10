from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
from database import Database
import logging
import time

logger = logging.getLogger(__name__)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def parse_bloomberg():
    try:
        url = "https://www.bloomberg.com/markets"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        news = []
        
        for article in soup.select('article.story-list-story'):
            title_elem = article.select_one('a.story-list-story__info__headline')
            if title_elem:
                title = title_elem.text.strip()
                link = 'https://www.bloomberg.com' + title_elem['href']
                news.append({'title': title, 'url': link})
        return news
    except Exception as e:
        logger.error(f"Error parsing Bloomberg: {e}")
        return []

def parse_kommersant():
    try:
        url = "https://www.kommersant.ru/"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        news = []
        
        for item in soup.select('.uho__link'):
            title = item.text.strip()
            link = item['href']
            if not link.startswith('http'):
                link = 'https://www.kommersant.ru' + link
            news.append({'title': title, 'url': link})
        return news
    except Exception as e:
        logger.error(f"Error parsing Kommersant: {e}")
        return []

def parse_reuters():
    try:
        url = "https://www.reuters.com/"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        news = []
        
        for article in soup.select('article.story'):
            title_elem = article.select_one('a[data-testid="Heading"]')
            if title_elem:
                title = title_elem.text.strip()
                link = 'https://www.reuters.com' + title_elem['href']
                news.append({'title': title, 'url': link})
        return news
    except Exception as e:
        logger.error(f"Error parsing Reuters: {e}")
        return []

def parse_tass():
    try:
        url = "https://tass.ru/"
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        news = []
        
        for item in soup.select('.news-card__title'):
            title = item.text.strip()
            link = item.find_parent('a')['href']
            if not link.startswith('http'):
                link = 'https://tass.ru' + link
            news.append({'title': title, 'url': link})
        return news
    except Exception as e:
        logger.error(f"Error parsing TASS: {e}")
        return []

def save_news_to_db(source_name, news_items):
    if not news_items:
        return
    
    db = Database()
    try:
        source = db.fetch_one("SELECT id FROM sources WHERE name = %s", (source_name,))
        
        if not source:
            logger.warning(f"Source not found: {source_name}")
            return
        
        for item in news_items:
            exists = db.fetch_one("SELECT id FROM news WHERE url = %s", (item['url'],))
            if not exists:
                db.execute(
                    "INSERT INTO news (source_id, title, url, published_at) VALUES (%s, %s, %s, %s)",
                    (source[0], item['title'], item['url'], datetime.now()),
                    commit=True
                )
                logger.info(f"Added news: {item['title'][:50]}...")
    except Exception as e:
        logger.error(f"Error saving news: {e}")
    finally:
        db.close()

def fetch_all_news():
    logger.info("Начало сбора новостей...")
    save_news_to_db('Bloomberg', parse_bloomberg())
    save_news_to_db('Коммерсантъ', parse_kommersant())
    save_news_to_db('Reuters', parse_reuters())
    save_news_to_db('ТАСС', parse_tass())
    logger.info("Сбор новостей завершен")