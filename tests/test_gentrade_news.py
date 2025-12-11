import pytest
from loguru import logger

from gentrade.news.factory import NewsAggregator, NewsFactory

from gentrade.news.meta import NewsFileDatabase
# from gentrade.news.newsapi import NewsApiProvider
# from gentrade.news.rss import RssProvider
# from gentrade.news.finnhub import FinnhubNewsProvider
# from gentrade.news.newsnow import NewsNowProvider

@pytest.mark.parametrize("provider_name",
                         [ "newsapi", "finnhub", "rss", "newsnow"])
def test_provider_basic(provider_name:str):
    db = NewsFileDatabase("news_db.txt")

    provider = NewsFactory.create_provider(provider_name)
    aggregator = NewsAggregator([ provider], db)
    aggregator.sync_news(
        category="business",
        max_hour_interval=64,
        max_count=10,
        process_content = True)

    # Log results
    all_news = db.get_all_news()
    logger.info(f"Total articles in database: {len(all_news)}")

    for news_item in all_news:
        logger.info("[%s...]: %s..." % (str(news_item.id)[:10], news_item.headline[:15]))
