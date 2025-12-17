import pytest
from loguru import logger

from gentrade.news.factory import NewsAggregator, NewsFactory

from gentrade.news.meta import NewsFileDatabase
from gentrade.news.providers.newsnow import AVAILABLE_SOURCE

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


@pytest.mark.parametrize("source",
                         AVAILABLE_SOURCE)
def test_provider_newsnow(source:str):
    db = NewsFileDatabase("news_db.txt")

    provider = NewsFactory.create_provider("newsnow", source=source)
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
