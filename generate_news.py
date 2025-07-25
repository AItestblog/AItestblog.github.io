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
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_articles]:
            articles.append({"title": entry.title, "summary": entry.get("summary", ""), "link": entry.link})
    return random.choice(articles) if articles else {"title": "找不到新聞", "summary": "請檢查來源或稍後重試。", "link": ""}

def extract_person_name(text, settings):
    prompt = settings.get("prompts", {}).get("personExtraction", "").format(text=text)
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
    name = res.choices[0].message.content.strip()
    return name if name != "無" else None

def generate_chinese_title(raw_title, settings):
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
