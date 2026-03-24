"""click_turnstile_shadowdom.py

Quest 3.1 — 坐标降维打击：定位 Shadow DOM 中的 Turnstile 并点击

目标：攻克 Turnstile 嵌套在 Shadow DOM / iframe 中的结构，
     通过多种方式定位 widget 坐标，实现物理点击。

边界限制：本关不需要处理点击后的数据抓取，只需完成「点击」动作。

验收标准：
    - 鼠标模拟点击了 Turnstile 验证区域
    - 点击后原本的 Turnstile 框消失，出现绿色勾（或页面标题变更）
"""
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
        await asyncio.sleep(3)  # 等待 CF JS 初始化

        title = await page.title()
        print(f"[*] 当前标题: {title}")

        clicked = False

        # === 方法1：遍历 page.frames，在 CF iframe 内查找 checkbox ===
        # Turnstile 的 checkbox input 有时可以直接用 locator 定位
        try:
            for f in page.frames:
                if "challenges.cloudflare.com" in f.url:
                    print(f"[*] 找到 CF iframe: {f.url[:80]}...")
                    checkbox = f.locator("input[type=checkbox]")
                    await checkbox.wait_for(timeout=8000)
                    await checkbox.click()
                    clicked = True
                    print("[✓] 方法1: 成功点击 iframe 内 checkbox")
                    break
        except Exception as e:
            print(f"[~] 方法1 未命中: {e}")

        # === 方法2：JS 穿透 iframe，直接调用 click() ===
        # 注意：跨域 iframe 通常无法访问 contentDocument，此法仅对同源有效
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
                    print("[✓] 方法2: JS 穿透点击成功")
                else:
                    print("[~] 方法2: 未找到 checkbox（跨域限制，正常）")
            except Exception as e:
                print(f"[~] 方法2 失败: {e}")

        # === 方法3：通过 getBoundingClientRect 获取 iframe 坐标，物理点击中心 ===
        # 这是最通用的方式：不依赖 iframe 内部结构，只需要 iframe 在页面上的位置
        if not clicked:
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
                    await page.mouse.click(rect["x"], rect["y"])
                    clicked = True
                    print(f"[✓] 方法3: 物理点击 iframe 中心 ({rect['x']:.1f}, {rect['y']:.1f})")
            except Exception as e:
                print(f"[~] 方法3 失败: {e}")

        # 等待验证结果
        await asyncio.sleep(5)

        title_after = await page.title()
        print(f"[*] 点击后标题: {title_after}")
        if "just a moment" not in title_after.lower() and "cloudflare" not in title_after.lower():
            print("[✓] 已通过 Turnstile 验证！")
        else:
            print("[~] 仍在验证页，可能需要更多等待")

        await page.screenshot(path="quest3_1_result.png")
        print("[*] 截图已保存: quest3_1_result.png")

        await asyncio.sleep(5)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
