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
        model='gemini-3-flash-preview',
        contents=contents
    )
    return response.text

def fill_application(url, user_info, client):
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print(f"Opening {url} in browser...")
    driver.get(url)
    time.sleep(3)
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
                    model='gemini-1.5-flash',
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
