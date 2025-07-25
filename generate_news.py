import os
import openai
import feedparser
import requests
import random
from datetime import datetime
import json

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_settings():
    with open('settings.txt', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_today_category(settings):
    weekday = datetime.utcnow().weekday()
    daily = settings.get("dailyCategories", [])
    return daily[weekday].get("category", "") if len(daily) > weekday else ""

def fetch_random_article(settings):
    articles = []
    weekday = datetime.utcnow().weekday()
    daily = settings.get("dailyCategories", [])
    feeds = daily[weekday].get("feeds", []) if len(daily) > weekday else []
    max_articles = settings.get("contentConfig", {}).get("maxArticlesPerFeed", 5)
    
    # 添加 User-Agent 以避免被網站擋住
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in feeds:
        try:
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_articles]:
                title = entry.get("title", "").strip()
                if not title:
                    continue  # 跳過沒有標題的項目
                articles.append({
                    "title": title,
                    "summary": entry.get("summary", "").strip(),
                    "link": entry.get("link", "").strip()
                })
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
    
    if articles:
        print(f"✅ 抓到 {len(articles)} 則有效新聞")
        return random.choice(articles)
    else:
        print("⚠️ 找不到有效新聞，使用預設新聞替代")
        return {
            "title": "Global markets show mixed trends amid Fed uncertainty",
            "summary": "Stocks in Asia gained slightly while U.S. markets await direction from upcoming earnings and Federal Reserve decisions.",
            "link": "https://example.com/fallback"
        }

def extract_person_name(text, settings):
    prompt = settings.get("prompts", {}).get("personExtraction", "").format(text=text)
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
    name = res.choices[0].message.content.strip()
    return name if name != "無" else None

def generate_chinese_title(raw_title, settings):
    if not raw_title.strip():
        return "（無法解析標題）"
    prompt = settings.get("prompts", {}).get("titleTranslation", "").format(raw_title=raw_title)
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7)
    return res.choices[0].message.content.strip()

def summarize_with_gpt(news, img_name, settings):
    prompt = settings.get("prompts", {}).get("articleSummary", "").format(
        title=news["title"], summary=news["summary"],
        word_count_min=settings.get("contentConfig", {}).get("wordCountMin", 1200),
        word_count_max=settings.get("contentConfig", {}).get("wordCountMax", 2000)
    )
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=4096)
    article = res.choices[0].message.content.strip().lstrip("```html").rstrip("```")
    image_tag = f'<img src="/{settings.get("contentConfig", {}).get("imagePath", "img/content/")}{img_name}">'
    parts = article.split("</p>", 1)
    article = parts[0] + "</p>" + image_tag + (parts[1] if len(parts) > 1 else "")
    return article.replace("\n", "").replace("  ", " ")

def generate_image(prompt_text, person_name, settings):
    full_prompt = settings.get("imagePrompts", {}).get("withPerson", "").format(person_name=person_name) if person_name else settings.get("imagePrompts", {}).get("withoutPerson", "").format(prompt_text=prompt_text[:200])
    res = client.images.generate(
        model=settings.get("imageConfig", {}).get("model", "dall-e-3"),
        prompt=full_prompt,
        size=settings.get("imageConfig", {}).get("size", "1024x1024"),
        quality=settings.get("imageConfig", {}).get("quality", "standard"),
        n=1
    )
    return requests.get(res.data[0].url).content

def get_next_image_id(settings):
    try:
        with open("last_image_id.txt", "r") as f:
            last = int(f.read().strip())
    except FileNotFoundError:
        last = settings.get("contentConfig", {}).get("initialImageId", 1)
    next_id = last + 1
    with open("last_image_id.txt", "w") as f:
        f.write(str(next_id))
    return next_id

def main():
    settings = load_settings()
    category = get_today_category(settings)
    print(f"▶️ 今日分類：{category}")
    news = fetch_random_article(settings)
    img_id = get_next_image_id(settings)
    img_name = f"{img_id}.jpg"
    img_alt = f"{img_id}-1.jpg"
    title = generate_chinese_title(news["title"], settings)
    person = extract_person_name(news["title"] + news["summary"], settings)
    article = summarize_with_gpt(news, img_name, settings)

    img_path = f"{settings.get('contentConfig', {}).get('imagePath', 'img/content/')}{img_name}"
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    image_bytes = generate_image(title, person, settings)
    with open(img_path, "wb") as f:
        f.write(image_bytes)

    today = datetime.now().strftime('%Y-%m-%d')
    block = f"title: {title}\nimages: {img_name},{img_alt}\nfontSize: {settings.get('contentConfig', {}).get('fontSize', '16px')}\ndate: {today}\ncontent: {article}<p>原始連結：<a href=\"{news['link']}\">點此查看</a></p>\n\n---\n"
    old = ""
    if os.path.exists("content.txt"):
        with open("content.txt", "r", encoding="utf-8") as f:
            old = f.read()
    with open("content.txt", "w", encoding="utf-8") as f:
        f.write(block + old)

    print(f"✅ 產出完成：{img_path} | 人物判斷：{person or '無'}")

if __name__ == "__main__":
    main()
