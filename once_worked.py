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
# ROBUST DROPDOWN HANDLER
# =============================

def select_option(page, label_text, option_text, retries=3):
    for attempt in range(1, retries + 1):
        try:
            log(f'Selecting "{option_text}" for "{label_text}" (attempt {attempt})')

            group = page.locator(
                f'.control-group:has(label:has-text("{label_text}"))'
            )
            group.wait_for(state="visible", timeout=15000)
            group.scroll_into_view_if_needed()

            button = group.locator(".dropdown-toggle")
            button.wait_for(state="visible", timeout=15000)
            button.click(force=True)

            menu = group.locator(".dropdown-menu")
            menu.wait_for(state="visible", timeout=15000)

            option = menu.locator(".filter-option", has_text=option_text).first
            option.wait_for(state="visible", timeout=15000)
            option.click(force=True)

            page.wait_for_timeout(400)

            selected_text = group.locator(".filter-text").inner_text()
            if option_text in selected_text:
                return

            raise TimeoutError("Selection did not stick")

        except TimeoutError:
            log("Retrying dropdown (DOM rebuilt)")
            page.wait_for_timeout(600)

    raise Exception(f'FAILED selecting "{option_text}" for "{label_text}"')

# =============================
# FORCE INTERNAL PRINTING
# =============================

def force_internal_printing(page, value):
    log("FORCING Internal/Text Pages Printing")

    for attempt in range(1, 4):
        log(f"  Attempt {attempt}")

        groups = page.locator(".filter-container.modular-filter .control-group")
        target = groups.nth(4)  # Internal/Text Pages Printing

        button = target.locator(".dropdown-toggle")
        button.wait_for(state="visible", timeout=15000)
        button.click(force=True)

        menu = target.locator(".dropdown-menu")
        menu.wait_for(state="visible", timeout=15000)

        option = menu.locator(".filter-option", has_text=value).first
        option.wait_for(state="visible", timeout=15000)
        option.click(force=True)

        page.wait_for_timeout(600)

        selected_text = target.locator(".filter-text").inner_text()
        if value in selected_text:
            log("  Internal printing locked ✅")
            page.wait_for_load_state("networkidle")
            return

    raise Exception("Internal/Text Pages Printing NOT locked")

# =============================
# PRICE FETCH
# =============================

def get_price(page):
    log("Clicking 'Select Quantity & Get Price'")
    page.click('text="Select Quantity & Get Price"')
    page.wait_for_selector(".product-price .price1", timeout=20000)
    price = page.locator(".product-price .price1").inner_text()
    return price.replace("$", "").strip()

# =============================
# MAIN
# =============================

with sync_playwright() as p:
    log("Launching browser")

    browser = p.firefox.launch(headless=False, slow_mo=120)
    page = browser.new_page()

    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")

    log("Page loaded")

    # Lock size ONCE
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
                select_option(page, "Cover Printing", cp)
                select_option(page, "Cover Stock", cs)
                select_option(page, "Cover Laminate (outside only)", lm)

                force_internal_printing(page, ip)

                select_option(page, "Internal/Text Pages Stock", ist)
                select_option(page, "Internal/Text Pages (pp) Excluding Cover", pg)

                for qty in QUANTITIES:
                    log(f"Processing quantity: {qty}")
                    select_option(page, "Quantity", qty)
                    price = get_price(page)
                    log(f"PRICE FOUND: {qty};;{price}")
                    f.write(f"{qty};;{price}\n")
                    time.sleep(1)

                f.write("\n\n")

            except Exception as e:
                log(f"CONFIG ERROR ❌ {e}")
                f.write("CONFIG ERROR\n\n")

    log("Closing browser")
    browser.close()

log("DONE ✔ Output written to A5_PERFECT_BOUND_OUTPUT.txt")
