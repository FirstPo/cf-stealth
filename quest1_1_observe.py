"""Quest 1.1: 观察 Cloudflare 拦截现象
不做任何绕过，只用标准 Playwright 访问目标，记录被拦截的表现。
"""
import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "https://nowsecure.nl"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 有头模式，可以看到浏览器
        page = await browser.new_page()

        print(f"[*] 正在访问: {TARGET_URL}")
        try:
            await page.goto(TARGET_URL, timeout=15000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[!] 导航异常: {e}")

        title = await page.title()
        print(f"[*] page.title() = '{title}'")

        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            print("[✗] 被 Cloudflare 拦截 — 符合预期！")
        else:
            print(f"[?] 标题不含 CF 关键词，当前标题: {title}")

        content = await page.content()
        if "403" in content or "Forbidden" in content:
            print("[✗] 页面内容含 403/Forbidden")

        print("[*] 等待 8 秒供观察...")
        await asyncio.sleep(8)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
