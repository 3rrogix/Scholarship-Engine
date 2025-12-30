import os
import json
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from google import genai
from googlesearch import search
import pdfplumber
def load_completed_scholarships():
    try:
        with open('links.txt', 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_completed_scholarships(completed):
    with open('links.txt', 'a') as f:  # Append
        for url in completed:
            f.write(url + '\n')

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

def save_user_info(info):
    with open('user_info.txt', 'w') as f:
        for key, value in info.items():
            if key in ['essays', 'transcript']:
                continue  # Skip long text fields
            f.write(f"{key}: {value}\n")

def is_scholarship_applicable(url, user_info):
    """Use Gemini to check if the scholarship is applicable based on grade level."""
    try:
        import requests
        response = requests.get(url, timeout=10)
        page_text = response.text[:5000]  # First 5000 chars
        prompt = f"Based on the following page text, is this scholarship applicable for a {user_info['grade_level']} student? Answer with 'yes' or 'no' only."
        prompt_with_text = f"{prompt}\n\n{page_text}"
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt_with_text
        )
        return 'yes' in response.text.lower()
    except:
        return True  # If can't check, assume applicable

def load_api_key():
    try:
        with open('api_key.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise ValueError("API key file 'api_key.txt' not found. Please create it with your Gemini API key.")

# Configure Gemini API
api_key = load_api_key()
client = genai.Client(api_key=api_key)

def get_user_info():
    """Collect user information via prompts, loading existing if available."""
    info = load_user_info()
    

    fields = [
        ('name', "Enter your full name: "),
        ('grade_level', "Enter your grade level (e.g., high school senior, college freshman, sophomore, junior, senior): "),
        ('gender', "Enter your gender (e.g., male, female, non-binary): "),
        ('sex_assigned_at_birth', "Enter your sex assigned at birth (male, female, ignore): "),
        ('preferences', "Enter your sexual orientation/preferences (e.g., straight, gay, bi, queer): "),
        ('race', "Enter your race: "),
        ('ethnicity', "Enter your ethnicity: "),
        ('school', "Enter your school: "),
        ('gpa_weighted', "Enter your weighted GPA (on a 4.0 scale): "),
        ('gpa_unweighted', "Enter your unweighted GPA (on a 4.0 scale): "),
        ('resident', "Are you a resident of your country? (yes/no): "),
        ('city', "Enter your city (for local scholarships, leave blank if not applicable): "),
        ('state', "Enter your state (for local scholarships, leave blank if not applicable): "),
    ]
    for key, prompt in fields:
        if key not in info or not info[key]:
            info[key] = input(prompt).strip()

    # Transcript
    if 'transcript_path' not in info:
        transcript_path = input("Enter path to transcript file (PDF or TXT), leave blank to skip: ").strip()
        info['transcript_path'] = transcript_path
        if not transcript_path:
            info['transcript'] = "N/A"
        else:
            info['transcript'] = extract_text_from_file(transcript_path)
    
    # Essays: load from essay1.txt, essay2.txt, etc.
    essays = []
    i = 1
    while True:
        filename = f'essay{i}.txt'
        try:
            with open(filename, 'r') as f:
                essays.append(f.read())
            i += 1
        except FileNotFoundError:
            break
    info['essays'] = essays
    
    # Extra details
    if 'country' not in info:
        info['country'] = input("Enter your country (optional): ") or None
    
    return info

def extract_text_from_file(file_path):
    """Extract text from PDF or TXT file."""
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
        return text
    elif file_path.endswith('.txt'):
        with open(file_path, 'r') as f:
            return f.read()
    else:
        return "Unsupported file type"

def search_scholarships(query, num_results=5):
    """Search for scholarships using Google."""
    results = list(search(query, num_results=num_results))
    return results

def analyze_page_with_gemini(image_path, prompt):
    """Use Gemini to analyze the screenshot."""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    # Use the correct Gemini SDK format for image input
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

def fill_application(url, user_info, test=False):
    """Navigate to URL, analyze, and fill form."""
    options = webdriver.ChromeOptions()
    # Never use headless mode, always show browser window
    # (No options.add_argument("--headless"))
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print(f"Opening {url} in browser...")
    driver.get(url)
    time.sleep(3)  # Wait for page load

    # Take screenshot
    screenshot_path = 'screenshot.png'
    driver.save_screenshot(screenshot_path)

    # Prompt for Gemini
    prompt = """
    Analyze this webpage screenshot. Describe all form fields (inputs, selects, textareas), their labels, types, IDs or names if visible, and for textareas, include the full prompt or question text.
    Also describe buttons and their purposes (e.g., submit, next).
    Provide the information in a structured JSON format like:
    {
        "fields": [
            {"label": "First Name", "type": "text", "selector": "#fname"},
            {"label": "Essay", "type": "textarea", "selector": "#essay", "prompt": "Tell us about yourself"},
            ...
        ],
        "buttons": [
            {"label": "Submit", "selector": "#submit"}
        ]
    }
    """

    analysis = analyze_page_with_gemini(screenshot_path, prompt)
    print("Gemini Analysis:", analysis)

    # Parse JSON (assuming Gemini returns valid JSON)
    try:
        data = json.loads(analysis)
    except:
        print("Failed to parse Gemini response as JSON.")
        input("Press enter to continue or 'q' to quit: ")
        driver.quit()
        os.remove(screenshot_path)
        return

    # Fill fields
    for field in data.get('fields', []):
        label = field['label'].lower()
        selector = field.get('selector')
        field_type = field.get('type')
        if not selector:
            continue
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
        except:
            continue

        if field_type == 'select':
            select = Select(element)
            if 'race' in label:
                select.select_by_visible_text(user_info['race'])
                print(f"Selected race: {user_info['race']}")
            elif 'ethnicity' in label:
                select.select_by_visible_text(user_info['ethnicity'])
                print(f"Selected ethnicity: {user_info['ethnicity']}")
            elif 'gender' in label:
                select.select_by_visible_text(user_info['gender'])
                print(f"Selected gender: {user_info['gender']}")
            # Add more
        elif field_type in ['text', 'textarea']:
            if 'name' in label:
                element.send_keys(user_info['name'])
                print(f"Filled name: {user_info['name']}")
            elif 'school' in label:
                element.send_keys(user_info['school'])
                print(f"Filled school: {user_info['school']}")
            elif 'gpa' in label:
                element.send_keys(user_info['gpa_weighted'])
                print(f"Filled GPA: {user_info['gpa_weighted']}")
            elif 'essay' in label or 'personal statement' in label or 'textarea' in field_type:
                prompt_text = field.get('prompt', label)
                essay_prompt = f"Write an essay responding to this prompt: {prompt_text}. Use the following information from the user: {user_info['essays']}"
                essay_response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=essay_prompt
                ).text
                element.send_keys(essay_response)
                print(f"Filled essay with generated response.")
            # Add more conditions

    # Click submit or next
    for button in data.get('buttons', []):
        if 'submit' in button['label'].lower():
            if test:
                print(f"Test mode: Would click submit button: {button['selector']}")
            else:
                driver.find_element(By.CSS_SELECTOR, button['selector']).click()
            break

    input("Done filling, press enter to continue: ")
    driver.quit()
    os.remove(screenshot_path)

def main():
    parser = argparse.ArgumentParser(description='Automated Scholarship Filler')
    parser.add_argument('--test', action='store_true', help='Run in test mode without submitting forms')
    args = parser.parse_args()

    user_info = get_user_info()
    save_user_info(user_info)
    
    # Check if all required fields are present
    required = ['name', 'grade_level', 'gender', 'race', 'school', 'gpa_weighted', 'resident', 'city', 'state']
    if not all(key in user_info and user_info[key] for key in required):
        print("Some required info missing. Run again to complete setup.")
        return
    

    print("\n--- Scholarship Search ---")
    print("You can search for scholarships by any criteria (e.g., major, interests, demographic, city, state, etc.)")
    print(f"Your saved city: {user_info.get('city', '')}, state: {user_info.get('state', '')}")
    print("If you want to include your city/state, mention them in your search.")
    search_query = input("Enter your scholarship search criteria (e.g., 'engineering scholarships for women in California'): ").strip()

    omit_criteria = input("Any specific criteria to omit (e.g., keywords, leave blank if none): ").strip()
    query = search_query
    if omit_criteria:
        query += f" -{omit_criteria}"

    num_results = int(input("How many links to search through on Google? ").strip())


    # Open Google search in browser for user to handle CAPTCHA if needed
    import urllib.parse
    search_terms = query
    city = user_info.get('city', '')
    state = user_info.get('state', '')
    if city and state and city.lower() not in search_terms.lower() and state.lower() not in search_terms.lower():
        search_terms += f" {city} {state}"
    encoded_query = urllib.parse.quote_plus(search_terms)
    url = f"https://www.google.com/search?q={encoded_query}"
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    input("If a CAPTCHA appears, please solve it in the browser. When you are done, press Enter here to continue...")
    import time
    from selenium.webdriver.common.by import By
    time.sleep(2)  # Wait for page to fully load
    # Load all completed/omitted links (strip off status/details if present)
    completed = set()
    try:
        with open('links.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    url = line.split('|', 1)[0].strip()
                else:
                    url = line.strip()
                if url:
                    completed.add(url)
    except FileNotFoundError:
        pass

    # Find all organic search result links
    organic_results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
    found_links = []
    for result in organic_results:
        try:
            link = result.find_element(By.CSS_SELECTOR, 'a')
            href = link.get_attribute('href')
            if href and href.startswith('http') and 'google.com' not in href and href not in completed and href not in found_links:
                found_links.append(href)
        except Exception:
            continue
    # Fallback: try all visible a[href] links if not enough found
    if len(found_links) < num_results:
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href]')
        for link in links:
            href = link.get_attribute('href')
            if href and href.startswith('http') and 'google.com' not in href and href not in completed and href not in found_links:
                found_links.append(href)
            if len(found_links) >= num_results:
                break

    # Process up to num_results links, skipping omitted/completed
    for idx, link_url in enumerate(found_links[:num_results]):
        if link_url in completed:
            print(f"Skipping omitted/completed link: {link_url}")
            continue
        print(f"Opening search result {idx+1}: {link_url}")
        driver.get(link_url)
        time.sleep(2)
        # Extract visible text from the page
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            page_text = ""

        # Detect CAPTCHA/Cloudflare/robot checks
        capcha_keywords = [
            'captcha', 'cloudflare', 'robot check', 'are you human', 'verify you are human',
            'please stand by', 'checking your browser', 'press and hold', 'security check',
            'unusual traffic', 'verify you are not a robot', 'solve the puzzle', 'protection from attacks'
        ]
        if any(word in page_text.lower() for word in capcha_keywords):
            print("CAPTCHA or anti-bot detected! Please solve it in the browser. After solving, press Enter to continue...")
            input("(Browser is paused for manual intervention)")
            # After user solves, try to reload text
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                page_text = ""

        # Use Gemini to analyze the text for scholarship/apply info
        prompt = (
            "Analyze the following webpage text. "
            "Does it contain a real scholarship opportunity, or is it just an ad for a university, or a scholarship only for attending that specific college/university? "
            "If it is a scholarship only for students who attend the same college/university as the page, treat it as 'not found'. "
            "If it is a real, general scholarship, is there a way to apply (e.g., a button or link with 'apply', 'application', or similar)? "
            "If the scholarship is closed or unavailable, say so. "
            "Summarize in JSON: {\"status\": 'open'|'closed'|'completed'|'not found', \"details\": <short reason>}"
        )
        from google import genai
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=f"{prompt}\n\n{page_text[:5000]}"
        )
        analysis = response.text
        print("Gemini Analysis:", analysis)
        # Try to parse Gemini's JSON response
        import json
        import re
        status = 'not found'
        details = ''
        # Remove code block markers if present
        cleaned = analysis.strip()
        if cleaned.startswith('```json'):
            cleaned = re.sub(r'^```json', '', cleaned).strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```', '', cleaned).strip()
        if cleaned.endswith('```'):
            cleaned = re.sub(r'```$', '', cleaned).strip()
        try:
            result = json.loads(cleaned)
            status = result.get('status', 'not found')
            details = result.get('details', '')
        except Exception:
            print("Could not parse Gemini response as JSON.")
            details = analysis
        # Save the link with status and details
        with open('links.txt', 'a') as f:
            f.write(f"{link_url} | {status} | {details}\n")
        print(f"Saved link with status: {status}")
        # Return to Google results page for next link
        driver.back()
        time.sleep(2)
    input("Press Enter to close the browser and finish...")
    driver.quit()

if __name__ == "__main__":
    main()