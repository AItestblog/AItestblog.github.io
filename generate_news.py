import feedparser
import random
from datetime import datetime

# 設定內嵌
settings = {
    "contentConfig": {
        "maxArticlesPerFeed": 5,
        "wordCountMin": 1200,
        "wordCountMax": 2000,
        "fontSize": "16px",
        "imagePath": "img/content/",
        "initialImageId": 1
    },
    "dailyCategories": [
        {
            "day": "周一",
            "category": "台股",
            "feeds": [
                "https://www.cnyes.com/rss/news/cat/tw_stock",
                "https://tw.stock.yahoo.com/rss/sitemap.xml",
                "https://money.udn.com/rssfeed/lists/10038",
                "https://www.businesstoday.com.tw/rss",
                "https://www.moneydj.com/rss/news.xml"
            ]
        },
        {
            "day": "周二",
            "category": "幣圈",
            "feeds": [
                "https://decrypt.co/feed",
                "https://cointelegraph.com/rss",
                "https://news.bitcoin.com/feed/",
                "https://www.theblock.co/rss",
                "https://www.coindesk.com/arc/outboundfeeds/rss/"
            ]
        },
        {
            "day": "周三",
            "category": "美股",
            "feeds": [
                "https://www.marketwatch.com/rss/topstories",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
                "https://www.bloomberg.com/feed/podcast/markets.xml",
                "https://www.nasdaq.com/feed/rssoutbound",
                "https://www.wsj.com/xml/rss/3_7085.xml"
            ]
        },
        {
            "day": "周四",
            "category": "ETF",
            "feeds": [
                "https://www.etftrends.com/feed/",
                "https://seekingalpha.com/tag/etf.rss",
                "https://www.etf.com/sections/news/rss",
                "https://www.morningstar.com/feeds/news.rss",
                "https://www.investopedia.com/feedbuilder/rssfeed"
            ]
        },
        {
            "day": "周五",
            "category": "黃金",
            "feeds": [
                "https://www.kitco.com/news/category/mining/rss",
                "https://www.kitco.com/rss/gold-live.xml",
                "https://www.gold.org/rss",
                "https://www.metal.com/rss/gold",
                "https://www.bullionvault.com/rss.xml"
            ]
        },
        {
            "day": "周六",
            "category": "外匯",
            "feeds": [
                "https://www.forexlive.com/feed/",
                "https://www.dailyfx.com/feeds/market-news",
                "https://www.fxstreet.com/rss",
                "https://www.investing.com/rss/forex.rss",
                "https://www.babypips.com/news/rss"
            ]
        },
        {
            "day": "周日",
            "category": "商品市場",
            "feeds": [
                "https://www.cmegroup.com/rss/market-news.rss",
                "https://www.barchart.com/commodities/rss",
                "https://www.investing.com/rss/commodities.rss",
                "https://www.reuters.com/arc/outboundfeeds/rss/commodities/",
                "https://www.bloomberg.com/feed/podcast/commodities.xml"
            ]
        }
    ]
}

# 抓今天的分類
def get_today_category():
    weekday = datetime.utcnow().weekday()
    daily = settings.get("dailyCategories", [])
    return daily[weekday] if len(daily) > weekday else {}

# 隨機選一篇新聞
def fetch_random_article(category_info):
    articles = []
    max_articles = settings["contentConfig"].get("maxArticlesPerFeed", 5)
    for url in category_info.get("feeds", []):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_articles]:
                if entry.get("title"):
                    articles.append({
                        "title": entry.title,
                        "summary": entry.get("summary", ""),
                        "link": entry.link
                    })
        except Exception as e:
            print(f"❌ 無法解析：{url} - {e}")
    return random.choice(articles) if articles else None

# 主流程
def main():
    category_info = get_today_category()
    print(f"📅 今日分類：{category_info.get('category', '無')}")
    article = fetch_random_article(category_info)
    if not article:
        print("❌ 找不到任何新聞，請稍後再試")
        return
    print(f"✅ 新聞標題：{article['title']}")
    print(f"🔗 原始連結：{article['link']}")
    print(f"📄 摘要（前150字）：{article['summary'][:150]}...")

if __name__ == "__main__":
    main()
