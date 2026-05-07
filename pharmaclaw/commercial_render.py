#!/usr/bin/env python3
import asyncio, os, glob
from playwright.async_api import async_playwright

FRAMES_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw/commercial_frames"
WIDTH = 1920
HEIGHT = 1080

async def render_all():
    html_files = sorted(glob.glob(os.path.join(FRAMES_DIR, "frame_*.html")))
    print(f"  Rendering {len(html_files)} frames...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        
        for idx, html_file in enumerate(html_files):
            png_file = html_file.replace(".html", ".png")
            await page.goto(f"file://{html_file}")
            await page.screenshot(path=png_file)
            if idx % 100 == 0:
                print(f"    {idx}/{len(html_files)} rendered")
        
        await browser.close()
    print(f"  Done rendering {len(html_files)} frames.")

asyncio.run(render_all())
