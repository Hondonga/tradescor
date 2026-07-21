#!/usr/bin/env python3
"""Chrome acceptance check for history-first Deriv chart loading."""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select,WebDriverWait
import requests

def main():
    options=webdriver.ChromeOptions();options.add_argument("--headless=new");options.add_argument("--window-size=1440,1000");options.set_capability("goog:loggingPrefs",{"browser":"ALL"})
    driver=webdriver.Chrome(options=options)
    try:
        driver.get("http://127.0.0.1:5000");wait=WebDriverWait(driver,25)
        driver.find_element(By.CSS_SELECTOR,'[data-page-link="chart"]').click()
        wait.until(lambda d:any(option.get_attribute("value")=="R_100" for option in d.find_elements(By.CSS_SELECTOR,'#symbol option[data-provider="deriv"]')))
        Select(driver.find_element(By.ID,"symbol")).select_by_value("R_100")
        wait.until(lambda d:d.find_element(By.ID,"chart-live").text in {"HISTORY","LIVE"})
        wait.until(lambda d:d.find_element(By.ID,"chart-price").text not in {"","--"})
        first_price=driver.find_element(By.ID,"chart-price").text
        wait.until(lambda d:d.find_element(By.ID,"chart-price").text!=first_price)
        live_price=driver.find_element(By.ID,"chart-price").text
        health=requests.get("http://127.0.0.1:5000/api/debug/deriv/live",timeout=10).json();assert health["active_subscription_count"]==1 and health["subscriptions"][0]["provider_symbol"]=="R_100"
        Select(driver.find_element(By.ID,"symbol")).select_by_value("R_75");wait.until(lambda d:"Volatility 75 Index" in d.find_element(By.ID,"chart-heading").text and d.find_element(By.ID,"chart-live").text in {"HISTORY","LIVE"})
        wait.until(lambda d:any(option.get_attribute("value")=="M15" for option in d.find_elements(By.CSS_SELECTOR,"#timeframe option")))
        driver.execute_script("const e=document.getElementById('timeframe');e.value='M15';e.dispatchEvent(new Event('change',{bubbles:true}));")
        wait.until(lambda d:"M15" in d.find_element(By.ID,"chart-heading").text and d.find_element(By.ID,"chart-live").text in {"HISTORY","LIVE"})
        canvases=driver.find_elements(By.CSS_SELECTOR,"#chart canvas");assert canvases,"Existing Lightweight Charts canvas was not rendered"
        logs=[row["message"] for row in driver.get_log("browser")];history=next((i for i,row in enumerate(logs) if "DERIV_CHART_SET_DATA_SUCCESS" in row),-1);live=next((i for i,row in enumerate(logs) if "DERIV_LIVE_STREAM_START" in row),-1)
        assert history>=0 and live>history,"Live stream started before successful historical setData"
        result={"heading":driver.find_element(By.ID,"chart-heading").text,"initial_r100_price":first_price,"updated_r100_price":live_price,"price":driver.find_element(By.ID,"chart-price").text,"canvas_count":len(canvases),"history_log_index":history,"live_log_index":live,"health":health["subscriptions"][0]}
        print("DERIV_BROWSER_ACCEPTANCE",result);driver.save_screenshot("/tmp/tradescor-deriv-chart.png")
    finally:driver.quit()
if __name__=="__main__":main()
