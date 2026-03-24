"""Quest 3.1: 定位 Shadow DOM 中的 Turnstile checkbox 并完成点击"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
TARGET_URL = "https://nowsecure.nl"

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
        await asyncio.sleep(3)

        title = await page.title()
        print(f"[*] 当前标题: {title}")

        # 尝试穿透 Shadow DOM 定位 Turnstile iframe 内的 checkbox
        clicked = False

        # 方法1: 通过 iframe 内 input[type=checkbox]
        try:
            frame = None
            for f in page.frames:
                url = f.url
                if "challenges.cloudflare.com" in url or "turnstile" in url:
                    frame = f
                    print(f"[*] 找到 CF iframe: {url}")
                    break

            if frame:
                checkbox = frame.locator("input[type=checkbox]")
                await checkbox.wait_for(timeout=8000)
                await checkbox.click()
                clicked = True
                print("[✓] 方法1: 成功点击 iframe 内 checkbox")
        except Exception as e:
            print(f"[~] 方法1 未命中: {e}")

        # 方法2: 穿透 Shadow DOM 用 JS 点击
        if not clicked:
            try:
                result = await page.evaluate("""
                    () => {
                        const iframes = document.querySelectorAll('iframe');
                        for (const iframe of iframes) {
                            try {
                                const doc = iframe.contentDocument || iframe.contentWindow.document;
                                const cb = doc.querySelector('input[type=checkbox]');
                                if (cb) { cb.click(); return 'clicked'; }
                            } catch(e) {}
                        }
                        return 'not_found';
                    }
                """)
                if result == 'clicked':
                    clicked = True
                    print("[✓] 方法2: JS 穿透 Shadow DOM 点击成功")
                else:
                    print("[~] 方法2: 未找到 checkbox")
            except Exception as e:
                print(f"[~] 方法2 失败: {e}")

        # 方法3: 直接点击页面上可见的 CF widget 区域
        if not clicked:
            try:
                widget = page.locator("[id*='cf-chl'], .cf-turnstile, [data-cf-turnstile], iframe")
                await widget.first.click(timeout=5000)
                clicked = True
                print("[✓] 方法3: 点击 CF widget 区域")
            except Exception as e:
                print(f"[~] 方法3 未命中: {e}")

        await asyncio.sleep(5)

        # 检查是否通过
        title_after = await page.title()
        print(f"[*] 点击后标题: {title_after}")
        if "just a moment" not in title_after.lower() and "cloudflare" not in title_after.lower():
            print("[✓] 已通过 Turnstile 验证！")
        else:
            print("[~] 仍在验证页，可能需要人工干预或更多等待")

        await page.screenshot(
            path="/Users/soleill/.openclaw/workspace/cf_stealth/quest3_1_result.png"
        )
        print("[*] 截图已保存: quest3_1_result.png")

        await asyncio.sleep(5)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
