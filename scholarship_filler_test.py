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
                    print(f"Clicked button/link with keyword: '{keyword}'")
                    return True
                except Exception:
                    continue
        return False

    # Loop: follow apply buttons/links until a form or login is detected
    max_steps = 5
    for step in range(max_steps):
        # Accept cookies if present (only on first step or if banner reappears)
        if step == 0:
            accept_cookies_if_present(driver)

        # Check for login form
        page_source = driver.page_source.lower()
        if 'login' in page_source or 'sign in' in page_source or 'log in' in page_source:
            print("Login page detected. Please log in manually if required.")
            input("After logging in, press Enter to continue...")
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

    # Now proceed with screenshot and Gemini analysis as before
    screenshot_path = 'screenshot.png'
    driver.save_screenshot(screenshot_path)
    prompt = """
    Analyze this webpage screenshot. Describe all form fields (inputs, selects, textareas), their labels, types, IDs or names if visible, and for textareas, include the full prompt or question text.
    Also describe buttons and their purposes (e.g., submit, next).
    Provide the information in a structured JSON format like:
    {"fields": [{"label": "First Name", "type": "text", "selector": "#fname"}], "buttons": [{"label": "Submit", "selector": "#submit"}]}
    """
    analysis = analyze_page_with_gemini(screenshot_path, prompt, client)
    print("Gemini Analysis:", analysis)
    try:
        data = json.loads(analysis)
    except Exception:
        print("Failed to parse Gemini response as JSON.")
        input("Press enter to continue or 'q' to quit: ")
        driver.quit()
        return
    for field in data.get('fields', []):
        label = field['label'].lower()
        selector = field.get('selector')
        field_type = field.get('type')
        if not selector:
            continue
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            continue
        if field_type == 'select':
            select = Select(element)
            if 'race' in label:
                select.select_by_visible_text(user_info.get('race', ''))
            elif 'ethnicity' in label:
                select.select_by_visible_text(user_info.get('ethnicity', ''))
            elif 'gender' in label:
                select.select_by_visible_text(user_info.get('gender', ''))
        elif field_type in ['text', 'textarea']:
            if 'name' in label:
                element.send_keys(user_info.get('name', ''))
            elif 'school' in label:
                element.send_keys(user_info.get('school', ''))
            elif 'gpa' in label:
                element.send_keys(user_info.get('gpa_weighted', ''))
            elif 'essay' in label or 'personal statement' in label or 'textarea' in field_type:
                prompt_text = field.get('prompt', label)
                essay_prompt = f"Write an essay responding to this prompt: {prompt_text}. Use the following information from the user: {user_info.get('essays', '')}"
                essay_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=essay_prompt
                ).text
                element.send_keys(essay_response)
    print("Filled out the form as best as possible. Please review and submit manually.")
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
