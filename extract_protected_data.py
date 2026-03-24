"""extract_protected_data.py

Quest 4.1 — 真金白银：提取受 CF 保护的真实业务数据

目标：在通过 CF Turnstile 验证后的 Session 中，提取目标网页的
     特定元素，并持久化为 result.json 文件。

边界限制：
    - 禁止频繁刷新页面，重点在「单次成功率」
    - 结果文件必须包含真实业务数据，而非 CF 拦截页的 HTML

验收标准：
    - 生成 result.json
    - 文件内容包含目标网站真实业务数据（标题不含 "Just a moment"）
"""
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
OUTPUT_PATH = "result.json"  # 输出到当前目录


def rand_sleep(lo: float = 0.5, hi: float = 2.0):
    """随机区间 sleep，避免固定延时被行为分析识别。"""
    return asyncio.sleep(random.uniform(lo, hi))


async def human_mouse_move(page, steps: int = 6):
    """模拟人类随机鼠标移动轨迹，欺骗 CF 行为分析。"""
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x = random.randint(200, vp["width"] - 200)
    y = random.randint(200, vp["height"] - 200)
    for _ in range(steps):
        tx = max(10, min(x + random.randint(-100, 100), vp["width"] - 10))
        ty = max(10, min(y + random.randint(-60, 60), vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await asyncio.sleep(random.uniform(0.04, 0.15))
        x, y = tx, ty


async def bypass_cf(page) -> bool:
    """检测并绕过 CF Turnstile 验证。

    通过遍历 page.frames 找到 CF 的 challenge iframe，
    获取其在页面中的坐标，模拟人类鼠标点击。

    Returns:
        bool: True 表示已通过验证（或无需验证）
    """
    await rand_sleep(1.5, 3.0)

    title = await page.title()
    # 如果标题不含 CF 关键词，说明已经通过了（stealth 效果很好时会直接过）
    if "just a moment" not in title.lower() and "cloudflare" not in title.lower():
        print("[✓] 无需点击，stealth 已直接通过 CF 验证")
        return True

    print("[*] 检测到 CF 挑战，模拟人类行为...")
    await human_mouse_move(page)  # 先做随机鼠标移动
    await rand_sleep(1.0, 2.5)

    # 查找 CF challenge iframe
    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            try:
                # 通过 JS 获取 iframe 在页面视口中的精确坐标
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
                    # 加随机偏移模拟人手不精准
                    cx = rect["x"] + random.uniform(-6, 6)
                    cy = rect["y"] + random.uniform(-5, 5)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.3, 0.7)
                    await page.mouse.click(cx, cy)
                    print(f"[*] 点击 Turnstile ({cx:.1f}, {cy:.1f})")
            except Exception as e:
                print(f"[~] 点击异常: {e}")
            break

    # 等待 CF 验证结果（不能硬编码固定时间）
    await rand_sleep(3.0, 5.0)
    title = await page.title()
    return "just a moment" not in title.lower() and "cloudflare" not in title.lower()


async def extract_data(page) -> dict:
    """从已通过验证的页面中提取真实业务数据。

    使用 BeautifulSoup 解析 HTML，提取标题、段落、链接和 meta 信息。
    注意：数据提取前会移除 script/style 噪声标签。
    """
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    # 移除不需要的噪声标签
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

    # 提取各级标题
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if text:
            data["headings"].append({"tag": h.name, "text": text})

    # 提取段落（过滤过短的无意义文本，取前10条）
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 20:
            data["paragraphs"].append(text)
        if len(data["paragraphs"]) >= 10:
            break

    # 提取外部链接（取前15条）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("http") and text:
            data["links"].append({"text": text, "href": href})
        if len(data["links"]) >= 15:
            break

    # 提取 meta 信息（description、keywords、og:title 等）
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

        # 尝试绕过 CF 验证
        passed = await bypass_cf(page)
        if not passed:
            print("[✗] 未能通过 CF 验证，退出。请检查网络或重试。")
            await browser.close()
            return

        print("[✓] 已通过 CF 验证，开始提取数据...")
        await rand_sleep(2.0, 3.0)  # 等页面完全渲染

        data = await extract_data(page)

        # 保存为 JSON 文件
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[✓] 数据已保存: {OUTPUT_PATH}")
        print(f"    标题: {data['title']}")
        print(f"    标题数: {len(data['headings'])}")
        print(f"    段落数: {len(data['paragraphs'])}")
        print(f"    链接数: {len(data['links'])}")

        # 验收判断：结果不能是 CF 拦截页
        if "just a moment" in data["title"].lower() or "cloudflare" in data["title"].lower():
            print("[✗] result.json 包含的是 CF 拦截页内容，非业务数据！")
        else:
            print("[✓] Quest 4.1 验收通过 — 真实业务数据已提取")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
