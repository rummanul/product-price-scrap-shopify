import csv
import time
from itertools import product
from playwright.sync_api import sync_playwright

URL = "https://www.cmykonline.com.au/booklets-magazines/perfect-binding/perfect-bound-48pp-plus/"

OUTPUT = "perfect_bound_all_quantities.csv"

# ======================
# OPTION SETS
# ======================

COVER_PRINTING = [
    "Full Colour (CMYK) one side",
    "Full Colour (CMYK) two sides"
]

COVER_STOCK = [
    "250gsm Gloss Artboard",
    "250gsm Matt-Satin Artboard",
    "250gsm Recycled Matt-Satin Artboard",
    "350gsm Gloss Artboard",
    "350gsm Matt-Satin Artboard",
    "350gsm Recycled Matt-Satin Artboard"
]

LAMINATE = [
    "Select ...",  # means no laminate
    "Gloss Laminate",
    "Matt Laminate",
    "Velvet Laminate"
]

INTERNAL_PRINTING = [
    "Full Colour (CMYK) two sides",
    "Black & White two sides"
]

INTERNAL_STOCK = [
    "100gsm Uncoated Bond",
    "115gsm Gloss Artpaper",
    "115gsm Matt-Satin Artpaper",
    "120gsm Uncoated Bond",
    "140gsm Uncoated Bond",
    "150gsm Gloss Artpaper",
    "150gsm Matt-Satin Artpaper",
    "170gsm Gloss Artpaper",
    "170gsm Matt-Satin Artpaper"
]

PAGES = [str(p) for p in range(48, 302, 2)]

QUANTITIES = [
    "5","10","15","20","25","30","40","50","60","70","80","90","100",
    "110","120","130","140","150","160","170","180","190","200","225","250","275","300"
]


# ======================
# HELPERS
# ======================

def select_option(page, label_text, option_text):
    label = page.locator(f'label:has-text("{label_text}")')
    dropdown = label.locator("..").locator(".dropdown-toggle")
    dropdown.click()
    page.wait_for_timeout(300)
    page.locator(f'.dropdown-menu >> text="{option_text}"').first.click()
    page.wait_for_timeout(300)


def get_price(page):
    page.click('text="Select Quantity & Get Price"')
    page.wait_for_selector(".product-price .price1", timeout=15000)
    return page.locator(".product-price .price1").inner_text().strip()


# ======================
# MAIN
# ======================

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL, timeout=60000)

    # FIX FINISHED SIZE
    select_option(page, "Finished Size (mm)", "A5 Portrait - 148x210")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Cover Printing",
            "Cover Stock",
            "Cover Laminate",
            "Internal Printing",
            "Internal Stock",
            "Pages",
            "Quantity",
            "Price"
        ])

        total = (
            len(COVER_PRINTING) * len(COVER_STOCK) * len(LAMINATE) *
            len(INTERNAL_PRINTING) * len(INTERNAL_STOCK) *
            len(PAGES) * len(QUANTITIES)
        )

        print(f"TOTAL combinations: {total}")

        count = 0

        for (
            cp,
            cs,
            lm,
            ip,
            isd,
            pg,
            qty
        ) in product(
            COVER_PRINTING,
            COVER_STOCK,
            LAMINATE,
            INTERNAL_PRINTING,
            INTERNAL_STOCK,
            PAGES,
            QUANTITIES
        ):

            try:
                select_option(page, "Cover Printing", cp)
                select_option(page, "Cover Stock", cs)
                select_option(page, "Cover Laminate (outside only)", lm)
                select_option(page, "Internal/Text Pages Printing", ip)
                select_option(page, "Internal/Text Pages Stock", isd)
                select_option(page, "Internal/Text Pages (pp) Excluding Cover", pg)
                select_option(page, "Quantity", qty)

                price_text = get_price(page)

                writer.writerow([cp, cs, lm, ip, isd, pg, qty, price_text])

                count += 1
                print(f"[{count}/{total}] {cp}, {cs}, {lm}, {ip}, {isd}, {pg}, {qty} → {price_text}")

                time.sleep(1.2)

            except Exception as e:
                print("FAILED at:", cp, cs, lm, ip, isd, pg, qty, " — reason:", e)
                time.sleep(2)

    browser.close()

print("DONE ✔")
