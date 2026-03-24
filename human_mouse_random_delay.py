"""human_mouse_random_delay.py

Quest 3.2 — 防抖动与随机延时：像人类一样等待

目标：引入随机鼠标轨迹和非固定延时，对抗 CF 的行为轨迹分析。
     CF 会统计点击的时间分布、鼠标移动路径等行为特征，
     固定延时（如 time.sleep(5)）会被识别为机器人模式。

边界限制：
    - 禁止使用 time.sleep(N) 硬编码固定值
    - 必须使用随机区间 random.uniform(lo, hi)

验收标准：连续运行 5 次，≥4 次成功通过 CF 验证进入目标页面。
"""
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
RUNS = 5  # 连续运行次数


def rand_sleep(lo: float = 0.5, hi: float = 2.0):
    """随机区间 sleep，模拟人类不规则的反应时间。
    永远不要用 asyncio.sleep(固定值)！
    """
    return asyncio.sleep(random.uniform(lo, hi))


async def human_mouse_move(page, steps: int = 8):
    """模拟人类随机鼠标移动轨迹。

    人类移动鼠标不是直线，而是带有随机偏移的曲线路径。
    CF 的行为分析会检测鼠标轨迹的「机械性」。
    """
    vp = page.viewport_size or {"width": 1440, "height": 900}
    x = random.randint(100, vp["width"] - 100)
    y = random.randint(100, vp["height"] - 100)

    for _ in range(steps):
        # 每步加随机偏移，模拟手部抖动
        tx = max(10, min(x + random.randint(-120, 120), vp["width"] - 10))
        ty = max(10, min(y + random.randint(-80, 80), vp["height"] - 10))
        await page.mouse.move(tx, ty)
        await asyncio.sleep(random.uniform(0.05, 0.2))  # 每步间隔也随机
        x, y = tx, ty


async def try_click_turnstile(page) -> bool:
    """定位 Turnstile iframe 并以随机延时模拟人类点击。

    Returns:
        bool: 是否成功触发点击
    """
    # 随机等待，模拟人类「看到页面」后思考的时间
    await rand_sleep(1.5, 3.5)

    # 点击前先随机移动鼠标，避免「瞬移到目标」的机械特征
    await human_mouse_move(page)
    await rand_sleep(0.8, 2.0)

    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            print("  [*] 找到 CF Turnstile iframe")
            try:
                # 获取 iframe 在页面中的精确坐标
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
                    # 加微小随机偏移，模拟人手点击不精准
                    cx = rect["x"] + random.uniform(-8, 8)
                    cy = rect["y"] + random.uniform(-6, 6)

                    # 先移动到附近，再移到目标，模拟人类接近动作
                    await page.mouse.move(cx - random.randint(20, 50), cy - random.randint(10, 30))
                    await rand_sleep(0.2, 0.5)
                    await page.mouse.move(cx, cy)
                    await rand_sleep(0.1, 0.3)
                    await page.mouse.click(cx, cy)
                    print(f"  [✓] 随机点击坐标 ({cx:.1f}, {cy:.1f})")
                    return True
            except Exception as e:
                print(f"  [~] 点击失败: {e}")
    return False


async def run_once(p, run_id: int) -> bool:
    """单次完整运行：启动浏览器 → 访问 → 绕过 → 检查结果。"""
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
        await rand_sleep(1.0, 2.0)  # 随机等待页面稳定

        title = await page.title()
        print(f"  [*] 初始标题: {title}")

        # 如果遇到 CF 挑战，尝试模拟人类点击
        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            print("  [~] 遇到 CF 挑战，模拟人类行为点击...")
            await try_click_turnstile(page)
            await rand_sleep(3.0, 5.0)  # 等待验证结果，时间也要随机
            title = await page.title()

        success = "just a moment" not in title.lower() and "cloudflare" not in title.lower()
        status = "✓ 通过" if success else "✗ 未通过"
        print(f"  [{status}] 最终标题: {title}")
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
                # 每次运行间也加随机间隔，避免固定频率被识别
                wait = random.uniform(2.0, 4.0)
                print(f"  [*] 下次运行前随机等待 {wait:.1f}s...")
                await asyncio.sleep(wait)

    # 汇总结果
    passed = sum(results)
    print(f"\n=== 汇总: {RUNS} 次中 {passed} 次通过 ===")
    for i, r in enumerate(results, 1):
        print(f"  第{i}次: {'✓ 通过' if r else '✗ 未通过'}")

    if passed >= 4:
        print("[✓] Quest 3.2 验收通过 (≥4/5)")
    else:
        print("[✗] 通过率不足，需进一步优化行为模拟")

if __name__ == "__main__":
    asyncio.run(main())
