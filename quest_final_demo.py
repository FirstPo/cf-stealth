"""成果验收: 对 Cloudflare 官方 Turnstile Demo 页面完整走一遍"""
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
TARGET_URL = "https://demo.turnstile.workers.dev"
OUTPUT_PATH = "/Users/soleill/.openclaw/workspace/cf_stealth/result_demo.json"


def rand_sleep(lo=0.5, hi=2.0):
    return asyncio.sleep(random.uniform(lo, hi))


async def human_mouse_move(page, steps=8):
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x, y = random.randint(200, vp["width"] - 200), random.randint(200, vp["height"] - 200)
    for _ in range(steps):
        tx = max(10, min(x + random.randint(-120, 120), vp["width"] - 10))
        ty = max(10, min(y + random.randint(-80, 80), vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await asyncio.sleep(random.uniform(0.04, 0.18))
        x, y = tx, ty


async def bypass_turnstile(page):
    """等待 Turnstile widget 出现并点击"""
    await rand_sleep(1.5, 3.0)
    await human_mouse_move(page)
    await rand_sleep(0.8, 1.5)

    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            print("[*] 找到 Turnstile iframe")
            try:
                rect = await page.evaluate("""
                    () => {
                        for (const f of document.querySelectorAll('iframe')) {
                            if (f.src && f.src.includes('challenges.cloudflare.com')) {
                                const r = f.getBoundingClientRect();
                                return {x: r.left + r.width/2, y: r.top + r.height/2, w: r.width, h: r.height};
                            }
                        }
                        return null;
                    }
                """)
                if rect and rect["w"] > 0:
                    cx = rect["x"] + random.uniform(-10, 10)
                    cy = rect["y"] + random.uniform(-8, 8)
                    await page.mouse.move(cx - 30, cy - 20)
                    await rand_sleep(0.2, 0.5)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.1, 0.3)
                    await page.mouse.click(cx, cy)
                    print(f"[✓] 点击 Turnstile widget ({cx:.1f}, {cy:.1f})")
                    await rand_sleep(3.0, 5.0)
                    return True
            except Exception as e:
                print(f"[~] 点击异常: {e}")
    return False


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
        await rand_sleep(1.0, 2.0)

        title = await page.title()
        print(f"[*] 初始标题: {title}")
        print(f"[*] CF iframe 数量: {sum(1 for f in page.frames if 'challenges.cloudflare.com' in f.url)}")

        # 截图：点击前
        await page.screenshot(path="/Users/soleill/.openclaw/workspace/cf_stealth/demo_before.png")
        print("[*] 截图(点击前): demo_before.png")

        # 点击 Turnstile
        clicked = await bypass_turnstile(page)
        print(f"[*] 点击结果: {'成功' if clicked else '未点击'}")

        # 截图：点击后
        await page.screenshot(path="/Users/soleill/.openclaw/workspace/cf_stealth/demo_after.png")
        print("[*] 截图(点击后): demo_after.png")

        # 检查 token 是否生成（Turnstile 通过后会填入隐藏 input）
        token = await page.evaluate("""
            () => {
                const el = document.querySelector('[name="cf-turnstile-response"]');
                return el ? el.value : null;
            }
        """)
        print(f"[*] cf-turnstile-response token: {'存在 ✓ (' + token[:20] + '...)' if token else '未生成'}")

        # 提取页面数据
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()

        result = {
            "url": page.url,
            "title": await page.title(),
            "turnstile_token_present": bool(token),
            "token_preview": token[:30] + "..." if token and len(token) > 30 else token,
            "headings": [h.get_text(strip=True) for h in soup.find_all(["h1","h2","h3"]) if h.get_text(strip=True)],
            "form_fields": [inp.get("name","") for inp in soup.find_all("input") if inp.get("name")],
        }

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] 结果已保存: {OUTPUT_PATH}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
