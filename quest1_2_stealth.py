"""Quest 1.2: 引入 playwright-stealth，移除 navigator.webdriver 特征"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

TARGET_URL = "https://nowsecure.nl"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()

        # 验证 navigator.webdriver 已被移除
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
            print("[~] 仍在 CF 验证页（Turnstile 阶段），stealth 起效但需点击验证 — 正常")
        else:
            print(f"[✓] 已进入目标页面: {title}")

        print("[*] 等待 10 秒供观察...")
        await asyncio.sleep(10)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
