import time
from itertools import product
from playwright.sync_api import sync_playwright, TimeoutError

URL = "https://www.cmykonline.com.au/booklets-magazines/perfect-binding/perfect-bound-48pp-plus/"
OUTPUT_FILE = "A5_PERFECT_BOUND_OUTPUT.txt"

# =============================
# OPTION MAPS
# =============================

COVER_PRINTING = {
    "Full Colour (CMYK) one side": "ones",
}

COVER_STOCK = {
    "250gsm Gloss Artboard": "250GA",
}

LAMINATE = {
    "Gloss Laminate": "G",
}

INTERNAL_PRINTING = {
    "Full Colour (CMYK) two sides": "FC",
}

INTERNAL_STOCK = {
    "100gsm Uncoated Bond": "100LU",
}

PAGES = ["48", "64"]
QUANTITIES = ["5", "10", "15", "20", "25"]

# =============================
# LOGGING
# =============================

def log(msg):
    print(f"[LOG] {msg}")

# =============================
# IMPROVED DROPDOWN HANDLER
# =============================

def select_option(page, label_text, option_text, retries=3):
    for attempt in range(1, retries + 1):
        try:
            log(f'Selecting "{option_text}" for "{label_text}" (attempt {attempt})')

            # Wait for page to settle
            page.wait_for_timeout(500)
            
            # Try different selectors for the control group
            group_selectors = [
                f'.control-group:has(label:has-text("{label_text}"))',
                f'.control-group:has(.filter-text:has-text("{label_text}"))',
                f'div.filter-container:has-text("{label_text}")'
            ]
            
            group = None
            for selector in group_selectors:
                try:
                    group = page.locator(selector).first
                    if group.count() > 0:
                        break
                except:
                    continue
            
            if not group:
                raise Exception(f'Could not find control group for "{label_text}"')
            
            group.wait_for(state="visible", timeout=15000)
            group.scroll_into_view_if_needed()
            
            # Wait for animation
            page.wait_for_timeout(300)
            
            # Try different ways to find and click the dropdown
            dropdown = group.locator(".dropdown-toggle").first
            dropdown.wait_for(state="visible", timeout=15000)
            
            # Click with more reliable method
            dropdown.click(force=True, timeout=10000)
            
            # Wait for menu to appear
            page.wait_for_timeout(400)
            
            # Look for the option
            option_selectors = [
                f'.dropdown-menu .filter-option:has-text("{option_text}")',
                f'.dropdown-menu li:has-text("{option_text}")',
                f'.dropdown-menu :text("{option_text}")'
            ]
            
            menu_option = None
            for selector in option_selectors:
                try:
                    menu_option = page.locator(selector).first
                    if menu_option.count() > 0:
                        break
                except:
                    continue
            
            if not menu_option:
                # Try to see available options
                available_options = page.locator('.dropdown-menu .filter-option').all_inner_texts()
                log(f"Available options: {available_options}")
                raise Exception(f'Option "{option_text}" not found in dropdown')
            
            menu_option.wait_for(state="visible", timeout=15000)
            
            # Click with position to avoid overlapping elements
            menu_option.click(force=True, position={"x": 10, "y": 10})
            
            # Wait for selection to apply
            page.wait_for_timeout(800)
            
            # Verify selection was made
            selected_text = group.locator(".filter-text").inner_text(timeout=5000)
            if option_text not in selected_text:
                log(f"Selection verification failed. Got: {selected_text}")
                continue
                
            log(f'Successfully selected "{option_text}"')
            return True

        except Exception as e:
            log(f"Attempt {attempt} failed: {str(e)[:100]}")
            if attempt < retries:
                log("Retrying dropdown...")
                page.wait_for_timeout(1000)
                # Try to close any open dropdowns
                page.click("body", position={"x": 10, "y": 10})
                page.wait_for_timeout(500)

    raise Exception(f'FAILED selecting "{option_text}" for "{label_text}" after {retries} attempts')

# =============================
# IMPROVED FORCE INTERNAL PRINTING
# =============================

def force_internal_printing(page, value):
    log("FORCING Internal/Text Pages Printing")

    for attempt in range(1, 4):
        log(f"  Attempt {attempt}")
        
        # Wait for dynamic content
        page.wait_for_timeout(500)
        
        # Clear any open dropdowns first
        page.click("body", position={"x": 10, "y": 10})
        page.wait_for_timeout(300)

        # Find the Internal/Text Pages Printing control group
        groups = page.locator(".filter-container.modular-filter .control-group")
        
        # Find by text content
        target = None
        for i in range(groups.count()):
            try:
                text = groups.nth(i).locator(".filter-text").inner_text(timeout=1000)
                if "Internal/Text Pages Printing" in text:
                    target = groups.nth(i)
                    break
            except:
                continue
        
        if not target:
            # Fallback to 5th element (as in original)
            target = groups.nth(4)
        
        target.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        
        button = target.locator(".dropdown-toggle").first
        button.wait_for(state="visible", timeout=10000)
        button.click(force=True)
        
        page.wait_for_timeout(400)
        
        # Try different ways to find and click the option
        option = None
        try:
            option = target.locator(f'.dropdown-menu :text("{value}")').first
            option.wait_for(state="visible", timeout=10000)
        except:
            # Try looking in the main document
            option = page.locator(f'.dropdown-menu :text("{value}")').first
        
        option.click(force=True, position={"x": 10, "y": 10})
        
        page.wait_for_timeout(800)
        
        # Verify selection
        selected_text = target.locator(".filter-text").inner_text(timeout=5000)
        if value in selected_text:
            log("  Internal printing locked ✅")
            return
        
        log(f"  Verification failed. Got: {selected_text}")

    raise Exception("Internal/Text Pages Printing NOT locked")

# =============================
# PRICE FETCH
# =============================

def get_price(page):
    log("Clicking 'Select Quantity & Get Price'")
    
    # Wait for button to be ready
    page.wait_for_timeout(500)
    
    # Try different ways to find and click the button
    button_selectors = [
        'text="Select Quantity & Get Price"',
        'button:has-text("Select Quantity & Get Price")',
        'a:has-text("Select Quantity & Get Price")'
    ]
    
    button = None
    for selector in button_selectors:
        try:
            button = page.locator(selector).first
            if button.count() > 0:
                break
        except:
            continue
    
    if not button:
        raise Exception("Could not find price button")
    
    button.scroll_into_view_if_needed()
    button.click(force=True)
    
    # Wait for price to load
    try:
        page.wait_for_selector(".product-price .price1", timeout=30000)
    except TimeoutError:
        # Try alternative selectors
        price_selectors = [".product-price .price1", ".price1", "[class*='price']"]
        for selector in price_selectors:
            try:
                page.wait_for_selector(selector, timeout=5000)
                break
            except:
                continue
    
    price = page.locator(".product-price .price1").first.inner_text(timeout=10000)
    return price.replace("$", "").strip()

# =============================
# MAIN EXECUTION
# =============================

def main():
    with sync_playwright() as p:
        log("Launching browser")
        
        # Use larger viewport to ensure all elements are visible
        browser = p.firefox.launch(
            headless=False,
            slow_mo=200,  # Increased for more reliability
            args=["--window-size=1400,900"]
        )
        
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=1
        )
        
        page = context.new_page()
        
        # Set longer timeouts
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(60000)
        
        log(f"Navigating to {URL}")
        page.goto(URL, wait_until="networkidle")
        
        # Wait for page to fully load
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        log("Page loaded")

        # Lock size once
        select_option(page, "Finished Size (mm)", "A5 Portrait - 148x210")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for cp, cs, lm, ip, ist, pg in product(
                COVER_PRINTING,
                COVER_STOCK,
                LAMINATE,
                INTERNAL_PRINTING,
                INTERNAL_STOCK,
                PAGES
            ):
                config_name = (
                    f"A5P_"
                    f"{COVER_PRINTING[cp]}_"
                    f"{COVER_STOCK[cs]}_"
                    f"{LAMINATE[lm]}_"
                    f"{INTERNAL_PRINTING[ip]}_"
                    f"{INTERNAL_STOCK[ist]}_"
                    f"pp{pg}"
                )

                log("=" * 60)
                log(f"START CONFIG: {config_name}")
                f.write(config_name + "\n\n")

                try:
                    # Clear any open dropdowns before starting new config
                    page.click("body", position={"x": 10, "y": 10})
                    page.wait_for_timeout(500)
                    
                    select_option(page, "Cover Printing", cp)
                    page.wait_for_timeout(600)
                    
                    select_option(page, "Cover Stock", cs)
                    page.wait_for_timeout(600)
                    
                    select_option(page, "Cover Laminate (outside only)", lm)
                    page.wait_for_timeout(600)
                    
                    force_internal_printing(page, ip)
                    page.wait_for_timeout(600)
                    
                    select_option(page, "Internal/Text Pages Stock", ist)
                    page.wait_for_timeout(800)  # Extra wait as this might trigger dynamic changes
                    
                    # SPECIAL HANDLING FOR PAGES DROPDOWN
                    log("Special handling for Pages dropdown...")
                    for pages_attempt in range(1, 4):
                        try:
                            select_option(
                                page,
                                "Internal/Text Pages (pp) Excluding Cover",
                                pg
                            )
                            log(f"Successfully selected {pg} pages")
                            break
                        except Exception as e:
                            log(f"Pages attempt {pages_attempt} failed: {str(e)[:100]}")
                            if pages_attempt < 3:
                                # Try resetting by selecting a different option first
                                try:
                                    alt_page = "64" if pg == "48" else "48"
                                    select_option(
                                        page,
                                        "Internal/Text Pages (pp) Excluding Cover",
                                        alt_page
                                    )
                                    page.wait_for_timeout(1000)
                                except:
                                    pass
                                page.wait_for_timeout(1000)
                            else:
                                raise

                    for qty in QUANTITIES:
                        log(f"Processing quantity: {qty}")
                        select_option(page, "Quantity", qty)
                        price = get_price(page)
                        log(f"PRICE FOUND: {qty};;{price}")
                        f.write(f"{qty};;{price}\n")
                        page.wait_for_timeout(800)

                    f.write("\n\n")

                except Exception as e:
                    log(f"CONFIG ERROR ❌ {e}")
                    f.write(f"CONFIG ERROR: {str(e)[:200]}\n\n")
                    # Try to recover by refreshing page
                    try:
                        page.reload(wait_until="networkidle")
                        page.wait_for_timeout(2000)
                        # Re-select size
                        select_option(page, "Finished Size (mm)", "A5 Portrait - 148x210")
                    except:
                        pass

        log("Closing browser")
        browser.close()

    log("DONE ✔ Output written to A5_PERFECT_BOUND_OUTPUT.txt")

if __name__ == "__main__":
    main()