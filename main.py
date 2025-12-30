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
            model='gemini-1.5-flash',
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
    ]
    
    for key, prompt in fields:
        if key not in info:
            info[key] = input(prompt).strip()
    
    # Conditional fields removed, asked every run
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
    contents = [
        prompt,
        {
            'mime_type': 'image/png',
            'data': image_data
        }
    ]
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=contents
    )
    return response.text

def fill_application(url, user_info, test=False):
    """Navigate to URL, analyze, and fill form."""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
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
            elif 'ethnicity' in label:
                select.select_by_visible_text(user_info['ethnicity'])
            elif 'gender' in label:
                select.select_by_visible_text(user_info['gender'])
            # Add more
        elif field_type in ['text', 'textarea']:
            if 'name' in label:
                element.send_keys(user_info['name'])
            elif 'school' in label:
                element.send_keys(user_info['school'])
            elif 'gpa' in label:
                element.send_keys(user_info['gpa'])
            elif 'essay' in label or 'personal statement' in label or 'textarea' in field_type:
                prompt_text = field.get('prompt', label)
                essay_prompt = f"Write an essay responding to this prompt: {prompt_text}. Use the following information from the user: {user_info['essays']}"
                essay_response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=essay_prompt
                ).text
                element.send_keys(essay_response)
            # Add more conditions

    # Click submit or next
    for button in data.get('buttons', []):
        if 'submit' in button['label'].lower():
            if test:
                print(f"Test mode: Would click submit button: {button['selector']}")
            else:
                driver.find_element(By.CSS_SELECTOR, button['selector']).click()
            break

    driver.quit()
    os.remove(screenshot_path)

def main():
    parser = argparse.ArgumentParser(description='Automated Scholarship Filler')
    parser.add_argument('--test', action='store_true', help='Run in test mode without submitting forms')
    args = parser.parse_args()

    user_info = get_user_info()
    save_user_info(user_info)
    
    # Check if all required fields are present
    required = ['name', 'grade_level', 'gender', 'race', 'school', 'gpa_weighted', 'resident']
    if not all(key in user_info and user_info[key] for key in required):
        print("Some required info missing. Run again to complete setup.")
        return
    
    # Ask for search criteria every time
    local = input("Do you want local scholarships? (yes/no): ").strip().lower()
    if local == 'yes':
        city = input("Enter your city: ").strip()
        state = input("Enter your state: ").strip()
        query_extra = f" in {city} {state}"
    else:
        query_extra = ""
    
    omit_criteria = input("Any specific criteria to omit (e.g., keywords, leave blank if none): ").strip()
    
    num_results = int(input("How many links to search through on Google? ").strip())
    
    query = f"scholarships for {user_info['grade_level']} {user_info['race']} {user_info['ethnicity']} students at {user_info['school']}{query_extra}"
    if omit_criteria:
        query += f" -{omit_criteria}"
    
    scholarships = search_scholarships(query, num_results)
    scholarships = [url for url in scholarships if is_scholarship_applicable(url, user_info)]
    completed = load_completed_scholarships()
    scholarships = [url for url in scholarships if url not in completed]  # Omit visited
    for url in scholarships:
        print(f"Filling application for: {url}")
        try:
            fill_application(url, user_info, test=args.test)
            if not args.test:
                save_completed_scholarships({url})  # Append this one
        except Exception as e:
            print(f"Failed to fill {url}: {e}")

if __name__ == "__main__":
    main()