from selenium import webdriver                            #to connect to google chrome, firefox, safari, etc. 

from selenium.webdriver.chrome.service import Service     #allow to access service of chrome

from selenium.webdriver.common.by import By               #to locate elements on a webpage

from selenium.webdriver.common.keys import Keys           #to use keyboard keys like ENTER, RETURN, etc.

import time                                               #to use sleep function

import google.generativeai as genai                       #import google gemini ai sdk



# ================= USER INPUT =================

query = input("Enter your news topic or query: ").strip()


# ================= SELENIUM SETUP =================

massenger = Service("chromedriver")                       #initialize service for chromedriver

driver = webdriver.Chrome()

driver.maximize_window() 

driver.get("https://indianexpress.com/search/")

search = driver.find_element(By.CLASS_NAME,"srch-npt")

time.sleep(3)

search.send_keys(query)                                   # for input in search bar
search.send_keys(Keys.RETURN)                             # for pressing enter key

time.sleep(3) 

for i in range(3):                                       # scroll multiple times to load more content
    driver.execute_script("window.scrollBy(0, 1000);")
    time.sleep(2)



# ================= SCRAPING =================


articles = driver.find_elements(By.CSS_SELECTOR, "div.search-result h3 a")  # locate article links


print("\n==================== SCRAPED RESULTS ====================\n")

news_data = []  # store results for Gemini input

for idx, a_tag in enumerate(articles[:5]):  # top 5 results
    try:
        title = a_tag.text.strip()
        link = a_tag.get_attribute("href")

        # try to get the nearest <p> below the headline
        try:
            desc = a_tag.find_element(By.XPATH, "./ancestor::div[contains(@class,'img-context')]/p").text.strip() 
            # Here we use an XPATH to locate a <p> tag that is near the article title
        except:
            desc = "No description available"

        news_entry = f"Title: {title}\nDescription: {desc}\nLink: {link}\n"
        news_data.append(news_entry)

        print(news_entry)
        print("-" * 80)
    except Exception as e:
        print(f"Skipping one article due to error: {e}")
        continue


time.sleep(10)

# Close the browser after scraping
driver.quit()



# ================= GEMINI AI INTEGRATION =================


# configure API key
genai.configure(api_key="api-key-here")

model = genai.GenerativeModel("gemini-2.0-flash")

# Combine scraped news + original query
combined_input = (
    f"Check the credibity of the news as of today: '{query}'\n\n"
    f"and provide key insights, tone, and overall summary in brief\n\n"
    f"also here is what i found for this news on indian express"+ "\n\n".join(news_data)
)

response = model.generate_content(combined_input)

print("\n==================== GEMINI AI RESULTS ====================\n")
print(response.text)


# ================= END OF SCRIPT ================= 
