import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from google import genai

def load_api_key():
    with open('api_key.txt', 'r') as f:
        return f.read().strip()

def load_user_info():
    info = {}
    try:
        with open('user_info.txt', 'r') as f:
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return info

def get_scholarship_links():
    links = []
    with open('links.txt', 'r') as f:
        for line in f:
            if '|' in line:
                url, status, *_ = [x.strip() for x in line.split('|')]
                if status.lower() == 'open':
                    links.append(url)
    return links

def analyze_page_with_gemini(image_path, prompt, client):
    with open(image_path, 'rb') as f:
        image_data = f.read()
    image_part = {
        'inline_data': {
            'mime_type': 'image/png',
            'data': image_data
        }
    }
    contents = [prompt, image_part]
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents
    )
    return response.text

def fill_application(url, user_info, client):
    def wait_for_form_or_input(driver, timeout=30):
        # Wait for a form, input, or textarea to appear
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                elements = driver.find_elements(By.XPATH, "//form | //input | //textarea")
                if elements:
                    return
            except Exception:
                pass
            time.sleep(0.5)
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Step 1: Sign in to Google account
    print("Opening Google sign-in page...")
    driver.get("https://accounts.google.com/signin")
    input("Please sign in to your Google account in the browser. After signing in, press Enter here to continue...")

    # Step 2: Open scholarship link and follow 'Apply' buttons until form or login
    print(f"Opening {url} in browser...")
    driver.get(url)
    time.sleep(3)

    # Keywords to look for in button/link text
    apply_keywords = [
        'apply now', 'apply here', 'go to form', 'start application', 'begin application',
        'start your application', 'continue to application', 'application form', 'apply', 'proceed to application'
    ]

    def accept_cookies_if_present(driver):
        # Try to accept cookies if the banner is present
        try:
            # Try common selectors for cookie accept buttons
            selectors = [
                "#onetrust-accept-btn-handler",
                "button[aria-label='Accept Cookies']",
                "button[title='Accept Cookies']",
                "button:contains('Accept Cookies')",
                "button:contains('Accept')",
                "button.cookie-accept",
                "button#accept-cookies"
            ]
            for selector in selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    element.click()
                    print("Accepted cookies using selector:", selector)
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            # Try by XPath as fallback
            xpaths = [
                "//button[contains(text(), 'Accept Cookies')]",
                "//button[contains(text(), 'Accept')]"
            ]
            for xpath in xpaths:
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    element.click()
                    print("Accepted cookies using XPath:", xpath)
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def find_and_click_apply(driver):
        # Try to find and click any button or link with apply-related keywords
        for keyword in apply_keywords:
            # Look for <a> or <button> elements containing the keyword (case-insensitive)
            xpath = f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')] | " \
                    f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                try:
                    # Get current window handles before click
                    old_handles = driver.window_handles
                    el.click()
                    time.sleep(3)
                    # Check if a new tab/window opened
                    new_handles = driver.window_handles
                    if len(new_handles) > len(old_handles):
                        # Switch to the newest tab
                        driver.switch_to.window(new_handles[-1])
                        print("Switched to new tab after clicking apply button.")
                        # Wait for the new page to finish loading and for a form/input to appear
                        wait_for_page_load(driver, timeout=30)
                        wait_for_form_or_input(driver, timeout=30)
                    else:
                        # Wait for the current page to finish loading and for a form/input to appear
                        wait_for_page_load(driver, timeout=30)
                        wait_for_form_or_input(driver, timeout=30)
                    print(f"Clicked button/link with keyword: '{keyword}'")
                    return True
                except Exception:
                    continue
        return False
    def wait_for_page_load(driver, timeout=15):
        # Wait for the page to finish loading by checking document.readyState
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                ready = driver.execute_script('return document.readyState')
                if ready == 'complete':
                    return
            except Exception:
                pass
            time.sleep(0.5)

    # Loop: follow apply buttons/links until a form or login is detected
    max_steps = 5
    for step in range(max_steps):
        # Accept cookies if present (only on first step or if banner reappears)
        if step == 0:
            accept_cookies_if_present(driver)

        # Wait for the page to finish loading
        wait_for_page_load(driver)

        # Check for login form (by keywords or password field)
        page_source = driver.page_source.lower()
        password_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
        if (
            'login' in page_source or 'sign in' in page_source or 'log in' in page_source or password_fields
        ):
            print("Login form detected. Please log in manually if required.")
            input("After logging in, press Enter to continue...")
            wait_for_page_load(driver)
            time.sleep(2)
            continue

        # Check for form fields (input, select, textarea)
        form_elements = driver.find_elements(By.XPATH, "//input | //select | //textarea")
        # Only proceed if there are multiple input fields (not just a search box)
        if len(form_elements) > 2:
            # Check if this is just a search form (e.g., only one text input with 'search' in placeholder)
            text_inputs = driver.find_elements(By.XPATH, "//input[@type='text']")
            if len(form_elements) == 1 and text_inputs:
                placeholder = text_inputs[0].get_attribute('placeholder')
                if placeholder and 'search' in placeholder.lower():
                    # This is just a search box, not a real form
                    pass
                else:
                    print("Form detected. Proceeding to fill the form.")
                    break
            else:
                print("Form detected. Proceeding to fill the form.")
                break

        # Try to find and click an apply button/link
        found = find_and_click_apply(driver)
        if not found:
            print("No more 'Apply' buttons/links found. Stopping navigation.")
            break
        time.sleep(2)
        # Accept cookies again in case new site/tab has a banner
        accept_cookies_if_present(driver)

    # Now analyze HTML elements directly and fill the form
    # Check for login page by scanning title and visible text for login-related keywords
    login_keywords = ['login', 'sign in', 'log in', 'account', 'authentication', 'password', 'user id', 'username']
    page_title = driver.title.lower()
    try:
        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
    except Exception:
        page_text = ''
    print(f"[DEBUG] Page title: {page_title}")
    print(f"[DEBUG] First 500 chars of page text: {page_text[:500]}")
    found_keywords = [kw for kw in login_keywords if kw in page_title or kw in page_text]
    print(f"[DEBUG] Detected login keywords: {found_keywords}")
    is_login_page = bool(found_keywords)
    if is_login_page:
        print("[DEBUG] Login page detected. Please log in manually if required.")
        input("After logging in, press Enter to continue...")
        wait_for_page_load(driver, timeout=30)
        wait_for_form_or_input(driver, timeout=30)

    print("[DEBUG] Analyzing HTML elements to fill the form...")
    try:
        # Fill text, email, number, and textarea fields
        input_fields = driver.find_elements(By.XPATH, "//input | //textarea")
        for element in input_fields:
            try:
                field_type = element.get_attribute('type') or element.tag_name
                name = (element.get_attribute('name') or '').lower()
                id_ = (element.get_attribute('id') or '').lower()
                placeholder = (element.get_attribute('placeholder') or '').lower()
                label = ''
                # Try to find associated label
                if id_:
                    label_els = driver.find_elements(By.XPATH, f"//label[@for='{id_}']")
                    if label_els:
                        label = label_els[0].text.lower()
                # Heuristics to fill fields
                value = ''
                if 'name' in name or 'name' in id_ or 'name' in label or 'name' in placeholder:
                    value = user_info.get('name', '')
                elif 'school' in name or 'school' in id_ or 'school' in label or 'school' in placeholder:
                    value = user_info.get('school', '')
                elif 'gpa' in name or 'gpa' in id_ or 'gpa' in label or 'gpa' in placeholder:
                    value = user_info.get('gpa_weighted', '')
                elif 'email' in name or 'email' in id_ or 'email' in label or 'email' in placeholder:
                    value = user_info.get('email', '')
                elif 'essay' in name or 'essay' in id_ or 'essay' in label or 'essay' in placeholder or 'personal statement' in label:
                    prompt_text = label or placeholder or name or id_
                    essay_prompt = f"Write an essay responding to this prompt: {prompt_text}. Use the following information from the user: {user_info.get('essays', '')}"
                    value = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=essay_prompt
                    ).text
                if value:
                    element.clear()
                    element.send_keys(value)
            except Exception:
                continue

        # Fill select fields
        select_fields = driver.find_elements(By.TAG_NAME, 'select')
        for element in select_fields:
            try:
                label = ''
                id_ = (element.get_attribute('id') or '').lower()
                name = (element.get_attribute('name') or '').lower()
                if id_:
                    label_els = driver.find_elements(By.XPATH, f"//label[@for='{id_}']")
                    if label_els:
                        label = label_els[0].text.lower()
                select = Select(element)
                if 'race' in label or 'race' in name:
                    select.select_by_visible_text(user_info.get('race', ''))
                elif 'ethnicity' in label or 'ethnicity' in name:
                    select.select_by_visible_text(user_info.get('ethnicity', ''))
                elif 'gender' in label or 'gender' in name:
                    select.select_by_visible_text(user_info.get('gender', ''))
            except Exception:
                continue

        # Try to click submit or next buttons
        button_keywords = ['submit', 'next', 'continue', 'apply', 'finish', 'save']
        # Try <button> and <input type='submit'>
        for keyword in button_keywords:
            # <button> elements
            buttons = driver.find_elements(By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]" )
            for btn in buttons:
                try:
                    btn.click()
                    print(f"Clicked button: {btn.text}")
                    time.sleep(2)
                    break
                except Exception:
                    continue
            # <input type='submit'> elements
            inputs = driver.find_elements(By.XPATH, f"//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]" )
            for inp in inputs:
                try:
                    inp.click()
                    print(f"Clicked submit input: {inp.get_attribute('value')}")
                    time.sleep(2)
                    break
                except Exception:
                    continue
        # Try <a> elements styled as buttons (e.g., class contains 'button' and text matches)
        for keyword in button_keywords:
            links = driver.find_elements(By.XPATH, f"//a[contains(@class, 'button') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]" )
            for link in links:
                try:
                    link.click()
                    print(f"Clicked link: {link.text}")
                    time.sleep(2)
                    break
                except Exception:
                    continue

        print("Filled out the form as best as possible. Please review and submit manually.")
        input("Press Enter to close the browser...")
        driver.quit()
    except Exception as e:
        print("Error while filling the form:", e)
        input("Press Enter to close the browser...")
        driver.quit()

def main():
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)
    user_info = load_user_info()
    links = get_scholarship_links()
    if not links:
        print("No open scholarship links found in links.txt.")
        return
    # For test, just use the first one
    url = links[0]
    fill_application(url, user_info, client)

if __name__ == "__main__":
    main()
