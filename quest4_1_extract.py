"""Quest 4.1: 通过 CF 验证后提取真实业务数据，保存为 result.json"""
import asyncio
import random
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
TARGET_URL = "https://nowsecure.nl"
OUTPUT_PATH = "/Users/soleill/.openclaw/workspace/cf_stealth/result.json"


def rand_sleep(lo=0.5, hi=2.0):
    return asyncio.sleep(random.uniform(lo, hi))


async def human_mouse_move(page, steps=6):
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x, y = random.randint(200, vp["width"] - 200), random.randint(200, vp["height"] - 200)
    for _ in range(steps):
        tx = max(10, min(x + random.randint(-100, 100), vp["width"] - 10))
        ty = max(10, min(y + random.randint(-60, 60), vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await asyncio.sleep(random.uniform(0.04, 0.15))
        x, y = tx, ty


async def bypass_cf(page):
    """等待并尝试绕过 CF Turnstile"""
    await rand_sleep(1.5, 3.0)
    title = await page.title()
    if "just a moment" not in title.lower() and "cloudflare" not in title.lower():
        return True  # 已经通过了

    print("[*] 检测到 CF 挑战，模拟人类行为...")
    await human_mouse_move(page)
    await rand_sleep(1.0, 2.5)

    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            try:
                rect = await page.evaluate("""
                    () => {
                        for (const f of document.querySelectorAll('iframe')) {
                            if (f.src && f.src.includes('challenges.cloudflare.com')) {
                                const r = f.getBoundingClientRect();
                                return {x: r.left + r.width/2, y: r.top + r.height/2};
                            }
                        }
                        return null;
                    }
                """)
                if rect:
                    cx = rect["x"] + random.uniform(-6, 6)
                    cy = rect["y"] + random.uniform(-5, 5)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.3, 0.7)
                    await page.mouse.click(cx, cy)
                    print(f"[*] 点击 Turnstile ({cx:.1f}, {cy:.1f})")
            except Exception as e:
                print(f"[~] 点击异常: {e}")
            break

    await rand_sleep(3.0, 5.0)
    title = await page.title()
    return "just a moment" not in title.lower() and "cloudflare" not in title.lower()


async def extract_data(page):
    """提取页面真实业务数据"""
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    # 移除 script/style 噪声
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    data = {
        "url": page.url,
        "title": await page.title(),
        "headings": [],
        "paragraphs": [],
        "links": [],
        "meta": {}
    }

    # 标题
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if text:
            data["headings"].append({"tag": h.name, "text": text})

    # 段落（取前10条非空)
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 20:
            data["paragraphs"].append(text)
        if len(data["paragraphs"]) >= 10:
            break

    # 链接（取前15条）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("http") and text:
            data["links"].append({"text": text, "href": href})
        if len(data["links"]) >= 15:
            break

    # Meta 信息
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property", "")
        content = meta.get("content", "")
        if name and content:
            data["meta"][name] = content

    return data


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        print(f"[*] 访问: {TARGET_URL}")
        await page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")

        passed = await bypass_cf(page)
        if not passed:
            print("[✗] 未能通过 CF 验证，退出")
            await browser.close()
            return

        print("[✓] 已通过 CF 验证，开始提取数据...")
        # 等页面完全渲染
        await rand_sleep(2.0, 3.0)

        data = await extract_data(page)

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[✓] 数据已保存: {OUTPUT_PATH}")
        print(f"    标题: {data['title']}")
        print(f"    标题数: {len(data['headings'])}")
        print(f"    段落数: {len(data['paragraphs'])}")
        print(f"    链接数: {len(data['links'])}")

        # 验证不是 CF 报错页
        if "just a moment" in data["title"].lower() or "cloudflare" in data["title"].lower():
            print("[✗] result.json 包含的是 CF 拦截页，非业务数据")
        else:
            print("[✓] Quest 4.1 验收通过 — 真实业务数据已提取")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
