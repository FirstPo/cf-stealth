"""Quest 2.1: 真实 User-Agent 与视口配置，访问 bot.sannysoft.com 验证指纹"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# 硬编码一个真实 macOS Chrome UA，避免 fake-useragent 联网失败
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
CHECK_URL = "https://bot.sannysoft.com"

async def main():
    print(f"[*] 使用 User-Agent: {USER_AGENT}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()

        print(f"[*] 正在访问: {CHECK_URL}")
        try:
            await page.goto(CHECK_URL, timeout=30000, wait_until="domcontentloaded")
            # 等页面 JS 跑完
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] 导航异常: {e}")

        title = await page.title()
        print(f"[*] page.title() = '{title}'")

        ua_val = await page.evaluate("navigator.userAgent")
        print(f"[*] 实际 navigator.userAgent = {ua_val}")
        if "headless" in ua_val.lower():
            print("[✗] UA 含 Headless 字样，会被识别")
        else:
            print("[✓] UA 不含 Headless — 符合预期")

        wd = await page.evaluate("navigator.webdriver")
        print(f"[*] navigator.webdriver = {wd}")

        # 截图保存结果
        await page.screenshot(
            path="/Users/soleill/.openclaw/workspace/cf_stealth/quest2_1_sannysoft.png",
            full_page=True
        )
        print("[✓] 截图已保存: quest2_1_sannysoft.png")

        print("[*] 等待 10 秒供观察...")
        await asyncio.sleep(10)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
