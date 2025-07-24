import os
import openai
import feedparser
import requests
import random
from datetime import datetime
import json

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_settings():
    try:
        with open('settings.txt', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading settings.txt: {e}")
        return {}

def get_today_category(settings):
    weekday = datetime.utcnow().weekday()
    return settings.get("dailyCategories", {}).get(str(weekday), {}).get("category", "")

def fetch_random_article(category, settings):
    articles = []
    feeds = settings.get("dailyCategories", {}).get(str(datetime.utcnow().weekday()), {}).get("feeds", [])
    max_articles = settings.get("contentConfig", {}).get("maxArticlesPerFeed", 5)
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_articles]:
                articles.append({
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link
                })
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
    return random.choice(articles) if articles else {
        "title": "找不到新聞", "summary": "請檢查來源或稍後重試。", "link": ""
    }

def extract_person_name(text, settings):
    prompt = settings.get("prompts", {}).get("personExtraction", "").format(text=text)
    if not prompt:
        return None
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    name = res.choices[0].message.content.strip()
    return name if name != "無" else None

def generate_chinese_title(raw_title, settings):
    prompt = settings.get("prompts", {}).get("titleTranslation", "").format(raw_title=raw_title)
    if not prompt:
        return raw_title
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return res.choices[0].message.content.strip()

def summarize_with_gpt(news, img_id, settings):
    prompt = settings.get("prompts", {}).get("articleSummary", "").format(
        title=news["title"],
        summary=news["summary"],
        word_count_min=settings.get("contentConfig", {}).get("wordCountMin", 1200),
        word_count_max=settings.get("contentConfig", {}).get("wordCountMax", 2000)
    )
    if not prompt:
        return ""
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096
    )
    article = res.choices[0].message.content.strip()
    for token in ["```html", "```"]:
        if article.startswith(token): article = article[len(token):]
        if article.endswith("```"): article = article[:-3]
    image_tag = f'<img src="/{settings.get("contentConfig", {}).get("imagePath", "img/content/")}{img_id}">'
    if "<p>" in article:
        parts = article.split("</p>", 1)
        article = parts[0] + "</p>" + image_tag + (parts[1] if len(parts) > 1 else "")
    else:
        article = image_tag + article
    return article.replace("\n", "").replace("  ", " ").strip()

def generate_image(prompt_text, person_name, settings):
    if person_name:
        full_prompt = settings.get("imagePrompts", {}).get("withPerson", "").format(person_name=person_name)
    else:
        full_prompt = settings.get("imagePrompts", {}).get("withoutPerson", "").format(prompt_text=prompt_text[:200])
    if not full_prompt:
        return None
    try:
        res = client.images.generate(
            model=settings.get("imageConfig", {}).get("model", "dall-e-3"),
            prompt=full_prompt,
            size=settings.get("imageConfig", {}).get("size", "1024x1024"),
            quality=settings.get("imageConfig", {}).get("quality", "standard"),
            n=settings.get("imageConfig", {}).get("n", 1),
        )
        image_url = res.data[0].url
        return requests.get(image_url).content
    except Exception as e:
        print("⚠️ Image generation failed:", e)
        return None

def get_next_image_id(settings):
    try:
        with open("last_image_id.txt", "r") as f:
            last = int(f.read().strip())
    except:
        last = settings.get("contentConfig", {}).get("initialImageId", 1)
    next_id = last + 1
    with open("last_image_id.txt", "w") as f:
        f.write(str(next_id))
    return next_id

def main():
    settings = load_settings()
    category = get_today_category(settings)
    print(f"▶️ 今日分類：{category}")
    news = fetch_random_article(category, settings)
    img_id = get_next_image_id(settings)
    img_name = f"{img_id}.jpg"
    img_alt = f"{img_id}-1.jpg"
    title = generate_chinese_title(news["title"], settings)
    person = extract_person_name(news["title"] + news["summary"], settings)
    article = summarize_with_gpt(news, img_name, settings)

    img_path = f"{settings.get('contentConfig', {}).get('imagePath', 'img/content/')}{img_name}"
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    image_bytes = generate_image(title, person, settings)
    if image_bytes:
        with open(img_path, "wb") as f:
            f.write(image_bytes)
    else:
        print("⚠️ 圖片生成失敗，跳過儲存。")

    today = datetime.now().strftime('%Y-%m-%d')
    block = f"""title: {title}
images: {img_name},{img_alt}
fontSize: {settings.get('contentConfig', {}).get('fontSize', '16px')}
date: {today}
content: {article}<p>原始連結：<a href="{news['link']}">點此查看</a></p>

---
"""
    if os.path.exists("content.txt"):
        with open("content.txt", "r", encoding="utf-8") as f:
            old = f.read()
    else:
        old = ""
    with open("content.txt", "w", encoding="utf-8") as f:
        f.write(block + "\n" + old)

    print(f"✅ 產出完成：{img_path} | 人物判斷：{person or '無'}")

if __name__ == "__main__":
    main()