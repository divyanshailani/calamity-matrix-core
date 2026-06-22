import os
import json
import asyncio
import random
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "reliefweb_shadow")
os.makedirs(OUT_DIR, exist_ok=True)

# Advanced Search URL: Format = Situation Report | Disasters = Earthquake, Flood, Wild Fire, Volcano
BASE_URL = "https://reliefweb.int/updates?search=format.name%3A%22Situation+Report%22+AND+%28disaster.type.name%3A%22Earthquake%22+OR+disaster.type.name%3A%22Flood%22+OR+disaster.type.name%3A%22Wild+Fire%22+OR+disaster.type.name%3A%22Volcano%22%29"

async def extract_report_details(page, url):
    await page.goto(url, wait_until="load", timeout=60000)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass # Ignore networkidle timeout on individual articles if they have tracking scripts that never idle
    # The Stealth Resiliency: Randomized delay to prevent UN OCHA IP bans
    await asyncio.sleep(random.uniform(2, 6))
    
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Title
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"
    
    # 2. Date
    date_tag = soup.find('time')
    date_str = date_tag.get_text(strip=True) if date_tag else "Unknown Date"
    
    # 3. Country / Metadata
    country_tags = soup.find_all('a', href=lambda href: href and '/country/' in href)
    countries = [tag.get_text(strip=True) for tag in country_tags]
    country = countries[0] if countries else "Unknown Country"
    
    # 4. Body Narrative
    # Look for the main article body
    body_div = soup.find('div', class_=lambda c: c and 'body' in c.lower())
    if not body_div:
        body_div = soup.find('article')
        
    narrative = ""
    if body_div:
        paragraphs = body_div.find_all('p')
        narrative = "\n".join([p.get_text(strip=True) for p in paragraphs])
        
    return {
        "url": url,
        "title": title,
        "date": date_str,
        "country": country,
        "narrative": narrative
    }

async def run_scraper():
    print("==================================================")
    print("  CALAMITY AI: ReliefWeb Shadow Extraction Node   ")
    print("==================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Setting a standard user-agent to bypass basic bot filters
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        current_url = BASE_URL
        reports_data = []
        total_extracted = 0
        checkpoint_idx = 1
        
        while current_url:
            print(f"[*] Scraping List Page: {current_url}")
            try:
                await page.goto(current_url, wait_until="load", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(random.uniform(2, 6))
                html = await page.content()
            except Exception as e:
                print(f"[-] Error loading list page: {e}")
                # We could try to retry here, but let's just abort this url
                break
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract all report links on the page
            article_links = soup.find_all('a', href=lambda href: href and '/report/' in href)
            report_urls = ["https://reliefweb.int" + a['href'] if a['href'].startswith('/') else a['href'] for a in article_links]
            # Deduplicate links to prevent redundant requests
            report_urls = list(dict.fromkeys(report_urls))
            
            if not report_urls:
                print("[-] No reports found on this page. DOM structure might have changed or end of results reached.")
                break
                
            print(f"  [+] Found {len(report_urls)} unique reports on this list.")
            
            # Extract deep content from each report
            for r_url in report_urls:
                try:
                    details = await extract_report_details(page, r_url)
                    reports_data.append(details)
                    total_extracted += 1
                    print(f"      -> Extracted: {details['title'][:60]}...")
                    
                    # Resilience: Checkpoint every 50 records
                    if len(reports_data) >= 50:
                        checkpoint_file = os.path.join(OUT_DIR, f"reliefweb_reports_checkpoint_{checkpoint_idx}.json")
                        with open(checkpoint_file, 'w', encoding='utf-8') as f:
                            json.dump(reports_data, f, indent=4, ensure_ascii=False)
                        print(f"  [*] Saved chunk checkpoint: {checkpoint_file}")
                        reports_data = []
                        checkpoint_idx += 1
                        
                except Exception as e:
                    print(f"      [-] Error parsing {r_url}: {e}")
            
            # Find the pagination 'Next' link
            next_btn = soup.find('a', string=lambda s: s and 'next' in s.lower())
            if next_btn and 'href' in next_btn.attrs:
                current_url = "https://reliefweb.int" + next_btn['href'] if next_btn['href'].startswith('/') else next_btn['href']
                print(f"[*] Proceeding to next page...")
            else:
                current_url = None
                print("[*] Reached final pagination limit.")
                
        # Flush any remaining un-checkpointed data
        if reports_data:
            checkpoint_file = os.path.join(OUT_DIR, f"reliefweb_reports_checkpoint_{checkpoint_idx}.json")
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, indent=4, ensure_ascii=False)
            print(f"  [*] Saved final chunk checkpoint: {checkpoint_file}")
            
        print("==================================================")
        print("  EXTRACTION COMPLETE                             ")
        print(f"  Total Narrative Reports Extracted: {total_extracted}")
        print("==================================================")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
