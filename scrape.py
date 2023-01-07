import datetime
import dataclasses
import pygsheets
import json
import time
from playwright.sync_api import sync_playwright
import re
import pywhatkit
import pyautogui
import keyboard
import logging
import sys
import os
from dotenv import load_dotenv

load_dotenv("sample.env")

logger = logging.getLogger("amazonpricetracker")
logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s--%(levelname)s--%(message)s",
    level=logging.INFO,
)

@dataclasses.dataclass
class ProductStructure:
    name: str
    price: int
    url: str
    model_number: str = "NA"
    date: datetime = datetime.datetime.now()


def send_alert(product_name: str = "Sample", product_price: int = 10):
    try:
        logger.info("Trying to type whatsapp message")
        pywhatkit.sendwhatmsg_instantly(
            os.getenv('PHONE_NUMBER'),
            f"!!! PRICE DROP !!!\n\nOn {product_name}.\n\nPrice is now *_{product_price}_*",
            wait_time=60,
            tab_close=False,
        )
        logger.info("Trying to send whatsapp message")
        time.sleep(2)
        pyautogui.click()
        time.sleep(1)
        keyboard.press_and_release("enter")
    except Exception as ex:
        logger.error(f"Error in sending message {str(ex)}")


def write_data_to_google_sheet(data: ProductStructure):
    try:
        logger.info("Writing to google sheets")
        client = pygsheets.authorize(service_file="<YOUR JSON FILE>")
        sh = client.open('Amazon_Price_Tracker')
        wks = sh.sheet1        
        wks.append_table(
            [json.dumps(
                    datetime.datetime.now(), indent=4, sort_keys=True, default=str
                ),
                data.name,
                data.model_number,
                data.url,
                data.price],
            start="A2",
            end=None,
            dimension="ROWS",
            overwrite=True,
        )
        data_as_df = wks.get_as_df()
        previous_price = data_as_df.Price.iloc[-2]
        current_price = data_as_df.Price.iloc[-1]
        if previous_price > current_price:              
            send_alert(product_name=data.name, product_price=data.price)
        logger.info("Completed writing to google sheets")
    except Exception as ex:
        logger.error(f"Error writing data to google sheet {str(ex)}")


def scrape_data():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            logger.info("Data scraping started")
            page.goto("https://www.amazon.in/")
            page.get_by_role("textbox", name="Search").click()
            page.get_by_role("textbox", name="Search").fill("legion 5i pro")
            page.get_by_role("textbox", name="Search").press("Enter")
            with page.expect_popup() as popup_info:
                page.get_by_role("link", name="Lenovo Legion 5 Pro Intel Core i7-12700H 16\" (40.64cm) QHD IPS 165Hz 500Nits Gaming Laptop (16GB/1TB SSD/Win 11/Office 2021/NVIDIA RTX 3060 6GB/Alexa/3 Month Game Pass/Storm Grey/2.49Kg), 82RF00DYIN").click()
            page1 = popup_info.value
            page.goto(page1.url)
            product_name, model = page.locator("#titleSection").all_inner_texts()[0].split(",")                        
            product_price = page.locator("#corePriceDisplay_desktop_feature_div").locator(".a-price-whole").all_inner_texts()[0] #1,64,990 
            integer_price = int(re.sub(r"[^\d]","",product_price))            
            data = ProductStructure(
                name=product_name,
                price=integer_price,
                model_number=model.strip(),
                url=page1.url
            )
            logger.info("Data scraping completed")
            return data
        except Exception as ex:
            logger.error(f"Error scraping data {str(ex)}")

    

if __name__ == "__main__":
    logger.info("Starting script")
    data: ProductStructure = scrape_data()
    write_data_to_google_sheet(data)    
    logger.info("Completed script")
