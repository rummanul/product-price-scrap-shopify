import time
from itertools import product
from playwright.sync_api import sync_playwright

URL = "https://www.cmykonline.com.au/booklets-magazines/perfect-binding/perfect-bound-48pp-plus/"

COVER_PRINTING = {"Full Colour (CMYK) one side": "ones"}
COVER_STOCK = {"250gsm Gloss Artboard": "250GA"}
LAMINATE = {"Gloss Laminate": "G"}
INTERNAL_PRINTING = {"Full Colour (CMYK) two sides": "FC"}
INTERNAL_STOCK = {"100gsm Recycled Uncoated Bond": "100RUB"}

OUTPUT_FILE = (
    f"A5P_{COVER_PRINTING['Full Colour (CMYK) one side']}_"
    f"{COVER_STOCK['250gsm Gloss Artboard']}_"
    f"{LAMINATE['Gloss Laminate']}_"
    f"{INTERNAL_PRINTING['Full Colour (CMYK) two sides']}_"
    f"{INTERNAL_STOCK['100gsm Recycled Uncoated Bond']}.txt"
)

print(OUTPUT_FILE)
# exit()


PAGES = list(range(106, 302, 2))
QUANTITIES = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 225, 250, 275, 300]


def log(msg):
    print(f"[LOG] {msg}")


def ensure_page_alive(page):
    if page.is_closed():
        raise Exception("Page was closed by widget reload")


# =====================================================
# PRINTIQ-SAFE DROPDOWN SELECTOR
# =====================================================
def select_option(page, label_text, value, retries=10):
    value_str = str(value)

    for attempt in range(1, retries + 1):
        try:
            ensure_page_alive(page)
            log(f'Selecting "{value_str}" for "{label_text}" (attempt {attempt})')

            group = page.locator(
                f'.control-group:has(label.control-label:has-text("{label_text}"))'
            )
            group.wait_for(state="visible", timeout=15000)
            group.scroll_into_view_if_needed()

            # Open dropdown (do NOT wait for menu visibility)
            group.locator("a.dropdown-toggle.filter-button").click(force=True)
            page.wait_for_timeout(200)  # allow animation frame

            menu = group.locator("ul.dropdown-menu")

            # Numeric option first
            numeric = menu.locator(f'li[data-value="{value_str}"] a.filter-option')
            if numeric.count() > 0:
                numeric.first.click(force=True)
            else:
                menu.locator(
                    "a.filter-option",
                    has_text=value_str
                ).first.click(force=True)

            page.wait_for_timeout(300)

            if value_str in group.locator(".filter-text").inner_text():
                return

            raise Exception("Selection did not stick")

        except Exception as e:
            log(f"Retrying dropdown: {e}")
            page.wait_for_timeout(600)

    raise Exception(f'FAILED selecting "{value_str}" for "{label_text}"')


# =====================================================
# FORCE INTERNAL PRINTING (Widget Resets It)
# =====================================================
def force_internal_printing(page, value):
    log("FORCING Internal/Text Pages Printing")

    for attempt in range(1, 4):
        try:
            ensure_page_alive(page)

            group = page.locator(
                '.control-group:has(label.control-label:has-text("Internal/Text Pages Printing"))'
            )
            group.wait_for(state="visible", timeout=15000)
            group.locator("a.dropdown-toggle.filter-button").click(force=True)
            page.wait_for_timeout(200)

            option = group.locator(
                "ul.dropdown-menu a.filter-option",
                has_text=value
            ).first

            option.click(force=True)
            page.wait_for_timeout(400)

            if value in group.locator(".filter-text").inner_text():
                log("Internal printing locked ✅")
                return

        except Exception as e:
            log(f"Retry internal printing: {e}")
            page.wait_for_timeout(600)

    raise Exception("Internal/Text Pages Printing NOT locked")


# =====================================================
# PRICE FETCH (COMMA-SAFE)
# =====================================================
def get_price(page):
    ensure_page_alive(page)

    page.locator(
        "a.btn.btn-success.continue-button.filter-price-button"
    ).click(force=True)

    page.wait_for_selector(".product-price .price1", timeout=20000)

    raw = page.locator(".product-price .price1").inner_text()

    return float(
        raw.replace("$", "").replace(",", "").strip()
    )


# =====================================================
# MAIN
# =====================================================
with sync_playwright() as p:
    log("Launching browser")
    browser = p.firefox.launch(headless=True, slow_mo=120)
    page = browser.new_page()

    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    log("Page loaded")

    
    cp = list(COVER_PRINTING.keys())[0]
    cs = list(COVER_STOCK.keys())[0]
    lm = list(LAMINATE.keys())[0]
    ip = list(INTERNAL_PRINTING.keys())[0]
    ist = list(INTERNAL_STOCK.keys())[0]

    time.sleep(3)
    select_option(page, "Finished Size (mm)", "A5 Portrait - 148x210")
    time.sleep(1)
    select_option(page, "Cover Printing", cp)
    time.sleep(1)
    select_option(page, "Cover Stock", cs)
    time.sleep(1)
    select_option(page, "Cover Laminate (outside only)", lm)
    time.sleep(1)
    force_internal_printing(page, ip)
    time.sleep(1)
    select_option(page, "Internal/Text Pages Stock", ist)

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
                time.sleep(1)
                select_option(page, "Internal/Text Pages (pp) Excluding Cover", pg)
                    
                # time.sleep(1)
                for qty in QUANTITIES:
                    try:
                        select_option(page, "Quantity", qty)
                        price = get_price(page)
                        print(f"{price} {price - 10:.2f}")
                        f.write(f"{qty};;{price - 10:.2f}\n")

                    except Exception as e:
                        log(f"QTY ERROR (qty={qty}) ❌ {e}")
                        f.write(f"{qty};;ERROR\n")
                        continue


                f.write("\n")

            except Exception as e:
                log(f"CONFIG ERROR ❌ {e}")
                f.write("CONFIG ERROR\n\n")

    log("Closing browser")
    browser.close()

log("DONE ✔ Output written to A5_PERFECT_BOUND_OUTPUT.txt")
