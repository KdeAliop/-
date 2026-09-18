import feedparser
import requests
import re, json, os, time
from time import mktime
from deep_translator import GoogleTranslator

# ================== الإعدادات ==================
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://discord.com/api/webhooks/1550501824325361775/k27KvE1-UAbDivqDdbiLdrb8doFKbRiSogCEagDauMF0X_MmiLaSRTiwyFZCrcYyviW-")

FEEDS = {
    "Phoronix":    "https://www.phoronix.com/rss.php",
    "OMG! Ubuntu": "https://www.omgubuntu.co.uk/feed",
    "9to5Linux":   "https://9to5linux.com/feed",
    "It's FOSS":   "https://itsfoss.com/rss/",
    "DistroWatch": "https://distrowatch.com/news/news-headlines.xml",
}

POSTED_FILE    = "posted_news.json"
MAX_PER_SOURCE = 5     # أقصى أخبار جديدة من كل مصدر في الدورة
MAX_AGE_HOURS  = 48    # لا تنشر أخبار أقدم من 48 ساعة
# ===============================================

translator = GoogleTranslator(source="auto", target="ar")

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

def translate(text):
    """ترجمة مع 3 محاولات عند الفشل"""
    if not text:
        return ""
    for _ in range(3):
        try:
            return translator.translate(text)
        except Exception:
            time.sleep(3)
    return text

def is_recent(entry):
    """هل الخبر حديث؟ (يمنع طوفان الأخبار القديمة في أول تشغيل)"""
    try:
        published = mktime(entry.published_parsed)
        age = (time.time() - published) / 3600
        return age <= MAX_AGE_HOURS
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
        return resp.status_code in (200, 204)
    except Exception:
        return False

def main():
    posted = load_posted()
    new_count = 0

    for source, url in FEEDS.items():
        sent = 0
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if sent >= MAX_PER_SOURCE:
                    break
                link = entry.get("link", "")
                if not link or link in posted or not is_recent(entry):
                    continue

                title   = translate(entry.get("title", "خبر جديد"))
                summary = translate(clean_html(entry.get("summary", "")))

                if send_embed(title, link, summary, source):
                    posted.add(link)
                    sent += 1
                    new_count += 1

                time.sleep(2)  # تفادي حظر الترجمة
        except Exception as e:
            print(f"خطأ في {source}: {e}")

    save_posted(posted)
    print(f"✅ تم نشر {new_count} خبر جديد")

if __name__ == "__main__":
    main()
