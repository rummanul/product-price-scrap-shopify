import time
from itertools import product
from playwright.sync_api import sync_playwright, TimeoutError

URL = "https://www.cmykonline.com.au/booklets-magazines/perfect-binding/perfect-bound-48pp-plus/"
OUTPUT_FILE = "A5_PERFECT_BOUND_OUTPUT.txt"

COVER_PRINTING = {"Full Colour (CMYK) one side": "ones"}
COVER_STOCK = {"250gsm Gloss Artboard": "250GA"}
LAMINATE = {"Gloss Laminate": "G"}
INTERNAL_PRINTING = {"Full Colour (CMYK) two sides": "FC"}
INTERNAL_STOCK = {"100gsm Uncoated Bond": "100LU"}

PAGES = list(range(48, 302, 2))
QUANTITIES = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 225, 250, 275, 300]

def log(msg):
    print(f"[LOG] {msg}")

def ensure_page_alive(page):
    if page.is_closed():
        raise Exception("Page was closed by widget reload")

# =====================================================
# UNIVERSAL DROPDOWN SELECTOR (TEXT + NUMERIC)
# =====================================================

def select_option(page, label_text, value, retries=3):
    value_str = str(value)

    for attempt in range(1, retries + 1):
        try:
            ensure_page_alive(page)
            log(f'Selecting "{value_str}" for "{label_text}" (attempt {attempt})')

            group = page.locator(
                f'.control-group:has(label:has-text("{label_text}"))'
            )
            group.wait_for(state="visible", timeout=15000)
            group.scroll_into_view_if_needed()

            group.locator(".dropdown-toggle").click(force=True)

            menu = group.locator(".dropdown-menu")
            menu.wait_for(state="attached", timeout=15000)

            # 🔑 NUMERIC OPTIONS → data-value
            numeric_li = menu.locator(f'li[data-value="{value_str}"] a.filter-option')

            if numeric_li.count() > 0:
                numeric_li.first.wait_for(state="visible", timeout=15000)
                numeric_li.first.click(force=True)
            else:
                # 🔑 TEXT OPTIONS
                option = menu.locator(
                    "a.filter-option",
                    has_text=value_str
                ).first
                option.wait_for(state="visible", timeout=15000)
                option.click(force=True)

            page.wait_for_timeout(400)

            if value_str in group.locator(".filter-text").inner_text():
                return

            raise TimeoutError("Selection did not stick")

        except Exception as e:
            log(f"Retrying dropdown: {e}")
            page.wait_for_timeout(600)

    raise Exception(f'FAILED selecting "{value_str}" for "{label_text}"')

# =====================================================
# FORCE INTERNAL PRINTING
# =====================================================

def force_internal_printing(page, value):
    log("FORCING Internal/Text Pages Printing")

    for attempt in range(1, 4):
        try:
            ensure_page_alive(page)
            log(f"  Attempt {attempt}")

            group = page.locator(
                '.control-group:has(label:has-text("Internal/Text Pages Printing"))'
            )
            group.wait_for(state="visible", timeout=15000)
            group.locator(".dropdown-toggle").click(force=True)

            option = group.locator(
                ".dropdown-menu a.filter-option",
                has_text=value
            ).first

            option.wait_for(state="visible", timeout=15000)
            option.click(force=True)

            page.wait_for_timeout(600)

            if value in group.locator(".filter-text").inner_text():
                log("  Internal printing locked ✅")
                page.wait_for_load_state("networkidle")
                return

        except Exception as e:
            log(f"Retry internal printing: {e}")
            page.wait_for_timeout(600)

    raise Exception("Internal/Text Pages Printing NOT locked")

# =====================================================
# PRICE FETCH
# =====================================================

def get_price(page):
    ensure_page_alive(page)
    page.click('text="Select Quantity & Get Price"')
    page.wait_for_selector(".product-price .price1", timeout=20000)
    return float(
        page.locator(".product-price .price1")
        .inner_text()
        .replace("$", "")
        .strip()
    )

# =====================================================
# MAIN
# =====================================================

with sync_playwright() as p:
    log("Launching browser")
    browser = p.firefox.launch(headless=False, slow_mo=120)
    page = browser.new_page()

    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    log("Page loaded")

    # First dropdown (text)
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
            config = (
                f"A5P_{COVER_PRINTING[cp]}_{COVER_STOCK[cs]}_"
                f"{LAMINATE[lm]}_{INTERNAL_PRINTING[ip]}_{INTERNAL_STOCK[ist]}_pp{pg}"
            )

            log("=" * 60)
            log(f"START CONFIG: {config}")
            f.write(config + "\n")

            try:
                select_option(page, "Cover Printing", cp)
                select_option(page, "Cover Stock", cs)
                select_option(page, "Cover Laminate (outside only)", lm)
                force_internal_printing(page, ip)
                select_option(page, "Internal/Text Pages Stock", ist)
                select_option(page, "Internal/Text Pages (pp) Excluding Cover", pg)

                for qty in QUANTITIES:
                    select_option(page, "Quantity", qty)
                    price = get_price(page)
                    f.write(f"{qty};;{price - 10:.2f}\n")

                f.write("\n")

            except Exception as e:
                log(f"CONFIG ERROR ❌ {e}")
                f.write("CONFIG ERROR\n\n")

    log("Closing browser")
    browser.close()

log("DONE ✔ Output written to A5_PERFECT_BOUND_OUTPUT.txt")
