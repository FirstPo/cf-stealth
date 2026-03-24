"""
observe_cf_block.py
====================
Quest 1.1 — 原力的觉醒：观察 Cloudflare 拦截现象

目标：
    使用标准 Playwright（无任何反检测措施）访问受 CF 保护的站点，
    观察并记录被拦截的表现：页面标题、403 错误、无限 Checking 循环。

学习要点：
    - 标准自动化浏览器在 CF 面前是「裸奔」的
    - CF 通过 navigator.webdriver、TLS 指纹等特征秒识机器人
    - 这是后续所有优化的「对照组基线」

验收标准：
    page.title() 包含 "Just a moment..." 或 "Cloudflare"
"""
import asyncio
from playwright.async_api import async_playwright

# 目标站点：一个专门用于测试 CF 防护的站点
TARGET_URL = "https://nowsecure.nl"


async def main():
    async with async_playwright() as p:
        # 使用标准 Chromium，不做任何伪装
        browser = await p.chromium.launch(headless=False)  # 有头模式，可观察
        page = await browser.new_page()

        print(f"[*] 正在访问: {TARGET_URL}")
        try:
            await page.goto(TARGET_URL, timeout=15000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[!] 导航异常（超时或被拒）: {e}")

        # 获取页面标题，判断是否被 CF 拦截
        title = await page.title()
        print(f"[*] page.title() = '{title}'")

        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            print("[✗] 被 Cloudflare 拦截 — 符合预期！后续章节将逐步解决这个问题")
        else:
            print(f"[?] 未被拦截或标题不含 CF 关键词，当前标题: {title}")

        # 检查页面内容是否含 403
        content = await page.content()
        if "403" in content or "Forbidden" in content:
            print("[✗] 页面内容含 403/Forbidden")

        # 保留浏览器8秒供观察
        print("[*] 等待 8 秒供观察...")
        await asyncio.sleep(8)
        await browser.close()
        print("[*] 完成")


if __name__ == "__main__":
    asyncio.run(main())
