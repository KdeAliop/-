import feedparser
import requests
import re, json, os, time
from time import mktime

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

FEEDS = {
    "Phoronix":    "https://www.phoronix.com/rss.php",
    "9to5Linux":   "https://9to5linux.com/feed",
    "It's FOSS":   "https://itsfoss.com/rss/",
    "DistroWatch": "https://distrowatch.com/news/news-headlines.xml",
}

POSTED_FILE    = "posted_news.json"
MAX_PER_SOURCE = 5
MAX_AGE_HOURS  = 48

def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_posted(posted):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(posted)[-2000:], f, ensure_ascii=False)

def clean_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def is_recent(entry):
    try:
        published = mktime(entry.published_parsed)
        return ((time.time() - published) / 3600) <= MAX_AGE_HOURS
    except Exception:
        return True

def send_embed(title, url, description, source):
    embed = {
        "title": f"📰 {title}",
        "url": url,
        "color": 3066993,
        "footer": {"text": f"المصدر: {source}"},
    }
    if description:
        embed["description"] = description[:400]
    try:
        resp = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)
        if resp.status_code not in (200, 204):
            print(f"   ⚠️ فشل الإرسال [{resp.status_code}]: {resp.text[:100]}")
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"   ⚠️ خطأ اتصال بالويبهوك: {e}")
        return False

def main():
    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL غير موجود في Secrets!")
        return

    posted = load_posted()
    print(f"📂 سجل المنشور سابقاً: {len(posted)} رابط")
    new_count = 0

    for source, url in FEEDS.items():
        sent = 0
        try:
            feed = feedparser.parse(url)
            total = len(feed.entries)
            for entry in feed.entries:
                if sent >= MAX_PER_SOURCE:
                    break
                link = entry.get("link", "")
                if not link or link in posted or not is_recent(entry):
                    continue

                title   = entry.get("title", "خبر جديد")
                summary = clean_html(entry.get("summary", ""))

                if send_embed(title, link, summary, source):
                    posted.add(link)
                    sent += 1
                    new_count += 1
                time.sleep(1)
            print(f"📡 {source}: {total} خبر في الفيد، أُرسل: {sent}")
        except Exception as e:
            print(f"❌ خطأ في {source}: {e}")

    save_posted(posted)
    print(f"{'✅' if new_count else 'ℹ️'} النتيجة: {new_count} خبر جديد")

if __name__ == "__main__":
    main()
