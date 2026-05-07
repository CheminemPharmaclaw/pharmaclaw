#!/usr/bin/env python3
import asyncio, os, glob
from playwright.async_api import async_playwright

async def render_all():
    html_files = sorted(glob.glob(os.path.join("/home/democritus/.openclaw/workspace/pharmaclaw/commercial_frames", "frame_*.html")))
    print(f"  Rendering {len(html_files)} frames...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        for idx, hf in enumerate(html_files):
            await page.goto(f"file://{hf}")
            await page.screenshot(path=hf.replace(".html", ".png"))
            if idx % 150 == 0:
                print(f"    {idx}/{len(html_files)}")
        await browser.close()
    print(f"  Done.")

asyncio.run(render_all())
