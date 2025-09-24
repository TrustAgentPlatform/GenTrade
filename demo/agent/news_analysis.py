
import logging
import json

from gentrade.news import NewsDatabase, NewsFactory, NewsAggregator

LOG = logging.getLogger(__name__)


def create_providers():
    newsapi_provider = NewsFactory.create_provider("newsapi")
    finnhub_provider = NewsFactory.create_provider("finnhub")
    rss1_provider = NewsFactory.create_provider("rss")

    return [
        newsapi_provider,
        finnhub_provider,
        rss1_provider
    ]

def start():
    db = NewsDatabase()
    aggregator = NewsAggregator(providers=create_providers(), db=db)

    aggregator.sync_news(category="business", max_hour_interval=64, max_count=10)
    aggregator.sync_news(
        ticker="AAPL",
        category="business",
        max_hour_interval=64,
        max_count=2
    )

    all_news = db.get_all_news()
    for index, item in enumerate(all_news):
        LOG.info(f"[{index}] {item.headline} ")

    news_dicts = [news.to_dict() for news in all_news]

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(news_dicts, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start()
