"""Quest 3.2: 随机延时与鼠标轨迹模拟，对抗 CF 行为分析"""
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
TARGET_URL = "https://nowsecure.nl"
RUNS = 5


def rand_sleep(lo=0.5, hi=2.0):
    """随机区间 sleep，绝不硬编码固定秒数"""
    t = random.uniform(lo, hi)
    return asyncio.sleep(t)


async def human_mouse_move(page, steps=8):
    """模拟人类随机鼠标移动轨迹"""
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x, y = random.randint(100, vp["width"] - 100), random.randint(100, vp["height"] - 100)
    for _ in range(steps):
        tx = x + random.randint(-120, 120)
        ty = y + random.randint(-80, 80)
        tx = max(10, min(tx, vp["width"] - 10))
        ty = max(10, min(ty, vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await rand_sleep(0.05, 0.2)
        x, y = tx, ty


async def try_click_turnstile(page):
    """尝试点击 Turnstile，先等 iframe 稳定，再随机延时点击"""
    # 等 CF iframe 加载
    await rand_sleep(1.5, 3.5)

    # 先做随机鼠标移动
    await human_mouse_move(page)

    # 找 CF iframe
    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            print(f"  [*] 找到 CF iframe")
            # 等 widget body 可见
            try:
                body = frame.locator("body")
                await body.wait_for(state="visible", timeout=8000)
            except Exception:
                pass
            # 随机延时后点击 iframe 中央
            await rand_sleep(0.8, 2.0)
            try:
                # 通过 JS 获取 iframe 在页面中的位置
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
                    # 加随机偏移模拟人手
                    cx = rect["x"] + random.uniform(-8, 8)
                    cy = rect["y"] + random.uniform(-6, 6)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.3, 0.8)
                    await page.mouse.click(cx, cy)
                    print(f"  [✓] 点击坐标 ({cx:.1f}, {cy:.1f})")
                    return True
            except Exception as e:
                print(f"  [~] 点击失败: {e}")
    return False


async def run_once(p, run_id):
    print(f"\n=== 第 {run_id}/{RUNS} 次运行 ===")
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

    try:
        await page.goto(TARGET_URL, timeout=25000, wait_until="domcontentloaded")
        await rand_sleep(1.0, 2.0)

        title = await page.title()
        print(f"  [*] 初始标题: {title}")

        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            print("  [~] 遇到 CF 挑战，尝试点击...")
            await try_click_turnstile(page)
            await rand_sleep(3.0, 5.0)
            title = await page.title()

        success = "just a moment" not in title.lower() and "cloudflare" not in title.lower()
        print(f"  [{'✓' if success else '✗'}] 最终标题: {title} — {'通过' if success else '未通过'}")
        return success
    except Exception as e:
        print(f"  [!] 异常: {e}")
        return False
    finally:
        await browser.close()


async def main():
    results = []
    async with async_playwright() as p:
        for i in range(1, RUNS + 1):
            ok = await run_once(p, i)
            results.append(ok)
            if i < RUNS:
                wait = random.uniform(2.0, 4.0)
                print(f"  [*] 下次运行前等待 {wait:.1f}s...")
                await asyncio.sleep(wait)

    passed = sum(results)
    print(f"\n=== 汇总: {RUNS} 次中 {passed} 次通过 ===")
    for i, r in enumerate(results, 1):
        print(f"  第{i}次: {'✓ 通过' if r else '✗ 未通过'}")
    if passed >= 4:
        print("[✓] Quest 3.2 验收通过 (≥4/5)")
    else:
        print("[✗] 通过率不足，需优化")

if __name__ == "__main__":
    asyncio.run(main())
