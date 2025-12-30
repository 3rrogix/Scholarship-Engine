# Scholarship-Engine

An AI-powered tool to automate filling out scholarship applications. It searches the web for scholarships, uses Gemini API to analyze web forms, and auto-fills fields based on user-provided information and essays.

## Features

- Collects user details: grade level (including college sophomore, junior, senior), gender, sex assigned at birth, sexual orientation, race, ethnicity, school, weighted/unweighted GPA (4.0 scale), transcript (optional), essays, etc.
- Searches for scholarships online based on grade level and demographics.
- Uses Gemini vision to scan and identify form fields and buttons.
- Auto-fills applicable fields and generates essay responses where possible.
- Tracks completed scholarships to avoid re-processing them.
- Leaves non-applicable fields for user review.

## Requirements

- Python 3.8+
- Google Gemini API key
- Chrome browser (for Selenium)

## Usage

Run `python main.py` and follow the prompts to input your information.

For testing without submitting forms, use `python main.py --test`. This will simulate filling but not actually submit.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
3. Create a file named `api_key.txt` in the project directory and paste your API key into it.
4. Run the program: `python main.py`

## How it works

- The program prompts for user information including personal details, essays, and file paths.
- Loads existing info from `user_info.txt` if available, and asks for any missing fields.
- Saves user info (except essays and transcript) to `user_info.txt` for future runs.
- Essays are loaded from `essay1.txt`, `essay2.txt`, etc., until no more files are found.
- It searches the web for relevant scholarships based on grade level and demographics.
- Filters out scholarships that are not applicable (e.g., college scholarships for high school students) using AI.
- For each applicable scholarship URL, it uses Selenium to load the page, takes a screenshot, and uses Gemini AI to analyze the form fields.
- It auto-fills fields where possible using the provided information and generates essays based on user essays.
- Fields that cannot be auto-filled are left for manual review (currently, the program attempts to fill all it can).

## Limitations

- Relies on Gemini accurately identifying form elements and providing valid CSS selectors.
- Web scraping may violate terms of service; use responsibly.
- Essay generation is based on provided essays; quality depends on input.