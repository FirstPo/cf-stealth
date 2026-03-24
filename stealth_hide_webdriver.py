"""stealth_hide_webdriver.py

Quest 1.2 — 换上隐身斗篷：引入 playwright-stealth

目标：通过 Stealth 插件移除浏览器自动化中常见的特征（如 navigator.webdriver），
     让浏览器看起来像真实用户，而不是自动化脚本。

边界限制：本关只处理「属性特征」，不处理点击逻辑。

验收标准：
    - navigator.webdriver = false 或 undefined
    - 页面不再直接 403，停留在 Turnstile 验证界面
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # playwright-stealth 2.x API

TARGET_URL = "https://nowsecure.nl"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # 对整个 context 注入 stealth，比对单个 page 注入更彻底
        # Stealth 会自动处理：webdriver、chrome runtime、plugins、languages 等
        await Stealth().apply_stealth_async(context)

        page = await context.new_page()

        # 验证：在页面加载前就检查 webdriver 属性
        wd = await page.evaluate("navigator.webdriver")
        print(f"[*] navigator.webdriver = {wd}")
        if not wd:
            print("[✓] webdriver 特征已隐藏 — 符合预期")
        else:
            print("[✗] webdriver 仍为 true，stealth 未生效")

        print(f"[*] 正在访问: {TARGET_URL}")
        try:
            await page.goto(TARGET_URL, timeout=20000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[!] 导航异常: {e}")

        title = await page.title()
        print(f"[*] page.title() = '{title}'")

        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            # stealth 起效但仍需点击 Turnstile，这是正常的第二道关卡
            print("[~] 仍在 CF 验证页（Turnstile 阶段），stealth 起效但需点击验证 — 正常")
        else:
            print(f"[✓] 已进入目标页面: {title}")

        print("[*] 等待 10 秒供观察...")
        await asyncio.sleep(10)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
