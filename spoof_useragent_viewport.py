"""spoof_useragent_viewport.py

Quest 2.1 — 身份克隆：真实 User-Agent 与视口配置

目标：手动配置匹配真实系统的 UA、视口、语言、时区，防止因
     「服务器版 Linux + Headless」特征被秒封。

边界限制：必须保留浏览器界面（headless=False），禁止无头模式。

验收标准：
    访问 bot.sannysoft.com，User-Agent 不含 "HeadlessChrome" 字样，
    主要检测项显示 Passed。截图保存为 quest2_1_sannysoft.png。
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# 使用真实 macOS Chrome UA，避免 fake-useragent 联网超时
# 格式：Mozilla/5.0 (操作系统) AppleWebKit/... Chrome/版本
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# 用于检测浏览器指纹的第三方工具站
CHECK_URL = "https://bot.sannysoft.com"

async def main():
    print(f"[*] 使用 User-Agent: {USER_AGENT}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 必须有头，无头模式特征明显
            args=[
                "--disable-blink-features=AutomationControlled",  # 关闭自动化控制标志
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},  # 常见 MacBook 分辨率
            locale="zh-CN",                            # 中文语言环境
            timezone_id="Asia/Shanghai",               # 上海时区，与 UA 系统一致
        )

        # 注入 stealth，隐藏剩余自动化特征
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        print(f"[*] 正在访问指纹检测站: {CHECK_URL}")
        try:
            await page.goto(CHECK_URL, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(3)  # 等待页面 JS 检测脚本跑完
        except Exception as e:
            print(f"[!] 导航异常: {e}")

        title = await page.title()
        print(f"[*] page.title() = '{title}'")

        # 验证实际注入的 UA
        ua_val = await page.evaluate("navigator.userAgent")
        print(f"[*] 实际 navigator.userAgent = {ua_val}")
        if "headless" in ua_val.lower():
            print("[✗] UA 含 Headless 字样，会被识别")
        else:
            print("[✓] UA 不含 Headless — 符合预期")

        # 验证 webdriver 属性
        wd = await page.evaluate("navigator.webdriver")
        print(f"[*] navigator.webdriver = {wd}")

        # 截图保存，供人工核查所有检测项是否为绿
        screenshot_path = "quest2_1_sannysoft.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[✓] 截图已保存: {screenshot_path}")

        print("[*] 等待 10 秒供观察...")
        await asyncio.sleep(10)
        await browser.close()
        print("[*] 完成")

if __name__ == "__main__":
    asyncio.run(main())
