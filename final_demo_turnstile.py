"""final_demo_turnstile.py

成果验收 — 对 Cloudflare 官方 Turnstile Demo 完整测试

目标：对 Cloudflare 官方提供的 Turnstile 演示页面走完完整流程：
     stealth 伪装 → 识别 Turnstile → 点击绕过 → 提取 token → 保存数据。

测试站点：https://demo.turnstile.workers.dev
    - 这是 CF 官方的 Turnstile 功能演示页
    - 使用测试用 sitekey（1x00000000000000000000AA），允许自动通过
    - 真实场景中 token 会是真实的加密字符串

输出文件：result_demo.json
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
TARGET_URL = "https://demo.turnstile.workers.dev"
OUTPUT_PATH = "result_demo.json"


def rand_sleep(lo: float = 0.5, hi: float = 2.0):
    """随机区间 sleep，模拟人类不规则反应时间。"""
    return asyncio.sleep(random.uniform(lo, hi))


async def human_mouse_move(page, steps: int = 8):
    """模拟随机鼠标轨迹，对抗 CF 行为分析。"""
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x = random.randint(200, vp["width"] - 200)
    y = random.randint(200, vp["height"] - 200)
    for _ in range(steps):
        tx = max(10, min(x + random.randint(-120, 120), vp["width"] - 10))
        ty = max(10, min(y + random.randint(-80, 80), vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await asyncio.sleep(random.uniform(0.04, 0.18))
        x, y = tx, ty


async def click_turnstile(page) -> bool:
    """定位并点击 Turnstile widget。

    流程：
    1. 随机等待 + 鼠标移动（模拟人类看到页面的反应时间）
    2. 遍历 page.frames 找到 CF challenge iframe
    3. 通过 getBoundingClientRect 获取 iframe 坐标
    4. 加随机偏移后物理点击
    5. 随机等待验证结果

    Returns:
        bool: 是否成功触发点击
    """
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
                                return {x: r.left + r.width/2, y: r.top + r.height/2,
                                        w: r.width, h: r.height};
                            }
                        }
                        return null;
                    }
                """)
                if rect and rect["w"] > 0:
                    # 模拟人类「接近然后点击」的鼠标动作
                    cx = rect["x"] + random.uniform(-10, 10)
                    cy = rect["y"] + random.uniform(-8, 8)
                    await page.mouse.move(cx - random.randint(20, 50), cy - random.randint(10, 30))
                    await rand_sleep(0.2, 0.5)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.1, 0.3)
                    await page.mouse.click(cx, cy)
                    print(f"[✓] 点击 Turnstile widget ({cx:.1f}, {cy:.1f})")
                    await rand_sleep(3.0, 5.0)  # 等待 CF 后台验证
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
        # 注入 stealth，隐藏所有自动化特征
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        print(f"[*] 访问: {TARGET_URL}")
        await page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")
        await rand_sleep(1.0, 2.0)

        title = await page.title()
        cf_frame_count = sum(1 for f in page.frames if "challenges.cloudflare.com" in f.url)
        print(f"[*] 初始标题: {title}")
        print(f"[*] 检测到 CF iframe 数量: {cf_frame_count}")

        # 截图记录点击前状态
        await page.screenshot(path="demo_before_click.png")
        print("[*] 截图(点击前): demo_before_click.png")

        # 尝试点击 Turnstile
        clicked = await click_turnstile(page)
        print(f"[*] 点击结果: {'成功' if clicked else '未找到可点击目标'}")

        # 截图记录点击后状态
        await page.screenshot(path="demo_after_click.png")
        print("[*] 截图(点击后): demo_after_click.png")

        # 检查 Turnstile token 是否已生成
        # 通过验证后，CF 会将 token 填入隐藏的 input[name="cf-turnstile-response"]
        token = await page.evaluate("""
            () => {
                const el = document.querySelector('[name="cf-turnstile-response"]');
                return el ? el.value : null;
            }
        """)
        if token:
            print(f"[✓] cf-turnstile-response token 已生成: {token[:30]}...")
        else:
            print("[~] token 未生成（可能需要更长等待时间）")

        # 提取页面数据
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()

        result = {
            "url": page.url,
            "title": await page.title(),
            "turnstile_token_present": bool(token),
            # 只保存 token 前30字符，避免泄露完整 token
            "token_preview": (token[:30] + "...") if token and len(token) > 30 else token,
            "headings": [
                h.get_text(strip=True)
                for h in soup.find_all(["h1", "h2", "h3"])
                if h.get_text(strip=True)
            ],
            # 表单字段列表，验证页面结构
            "form_fields": [
                inp.get("name", "")
                for inp in soup.find_all("input")
                if inp.get("name")
            ],
        }

        # 保存结果
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] 结果已保存: {OUTPUT_PATH}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        await asyncio.sleep(5)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
