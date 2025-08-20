import time
import os
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- USER CONFIGURATION ---
# IMPORTANT: Replace with your Google account credentials
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "selenium_chrome_profile")
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data_wall")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- REQUEST CONFIGURATION ---
# Enter your request here between the triple quotes
STORY_TEXT = """Giyu ,tanjiro """
# Request title for filename (optional)
STORY_TITLE = ""

# --- REQUEST PROMPT TEMPLATE ---
# Since the model is already trained at the specific link, we just send the request directly
STORY_ANALYSIS_PROMPT = "{story_text}"

def authenticate_google(driver, wait):
    """Handle Google authentication"""
    print("Checking if login is required...")
    
    if "accounts.google.com" in driver.current_url or "signin" in driver.current_url:
        print("Login required. Performing login...")
        
        try:
            # Enter email
            email_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_field.clear()
            email_field.send_keys(GOOGLE_EMAIL)
            
            # Click next button
            next_button = driver.find_element(By.ID, "identifierNext")
            next_button.click()
            print("Email entered.")
            time.sleep(2)
            
        except TimeoutException:
            print("Email field not found, assuming it's pre-filled or different flow.")
        
        try:
            # Enter password
            password_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_field.clear()
            password_field.send_keys(GOOGLE_PASSWORD)
            
            # Click next button
            password_next = driver.find_element(By.ID, "passwordNext")
            password_next.click()
            print("Password entered. Login successful.")
            
            # Wait for redirect
            print("Waiting for login completion...")
            time.sleep(5)
            
        except TimeoutException:
            print("Password field not found or login already completed.")
    else:
        print("Already logged in or no login required.")

def read_latest_gemini_response(driver, wait):
    """Read the latest response from the current Gemini conversation"""
    print("Reading the latest response from Gemini conversation...")
    
    try:
        # Wait a moment for the page to settle
        time.sleep(3)
        
        # Try multiple selectors to find response content
        response_selectors = [
            # Gemini-specific selectors (most likely)
            "[data-message-author-role='model']",
            ".model-response-text",
            ".response-container",
            "[role='presentation']",
            ".markdown",
            ".message-content",
            
            # Generic selectors as fallback
            ".conversation .message:last-child",
            ".chat-message:last-child",
            "main .message:last-child"
        ]
        
        response_text = ""
        response_element = None
        
        for selector in response_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Get the last (most recent) response element
                    for element in reversed(elements):
                        if element.is_displayed():
                            text = element.get_attribute('textContent') or element.text
                            if text and len(text.strip()) > 100:  # Ensure it's substantial content
                                response_text = text.strip()
                                response_element = element
                                print(f"Found response using selector: {selector}")
                                break
                    if response_text:
                        break
            except Exception as e:
                print(f"Selector '{selector}' failed: {e}")
                continue
        
        # If no specific selectors work, try to get the main conversation content
        if not response_text:
            print("Trying to extract from main conversation area...")
            try:
                main_selectors = [
                    "main",
                    ".conversation",
                    ".chat-container",
                    "#main-content",
                    ".content"
                ]
                
                for main_selector in main_selectors:
                    try:
                        main_element = driver.find_element(By.CSS_SELECTOR, main_selector)
                        full_text = main_element.get_attribute('textContent') or main_element.text
                        
                        # Try to extract the last substantial block of text
                        # Look for patterns that indicate a Gemini response
                        if full_text:
                            # Split by common separators and get the last substantial chunk
                            chunks = full_text.split('\n\n')
                            for chunk in reversed(chunks):
                                if len(chunk.strip()) > 200 and ('Scene' in chunk or 'scene' in chunk):
                                    response_text = chunk.strip()
                                    print(f"Extracted response from main content using {main_selector}")
                                    break
                            if response_text:
                                break
                    except:
                        continue
            except Exception as e:
                print(f"Error extracting from main content: {e}")
        
        if response_text:
            print(f"Successfully extracted response ({len(response_text)} characters)")
            print(f"Response preview: {response_text[:200]}...")
            return response_text
        else:
            print("❌ Could not find any response content on the page")
            
            # Debug: Save screenshot and page source
            print("Saving debug information...")
            driver.save_screenshot(os.path.join(OUTPUT_DIR, f"debug_no_response_{int(time.time())}.png"))
            
            # Try to get all text content for debugging
            try:
                all_text = driver.find_element(By.TAG_NAME, "body").text
                debug_file = os.path.join(OUTPUT_DIR, f"debug_page_content_{int(time.time())}.txt")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("=== FULL PAGE TEXT ===\n")
                    f.write(all_text)
                print(f"Full page content saved to: {debug_file}")
            except:
                pass
            
            return None
            
    except Exception as e:
        print(f"Error reading response: {e}")
        return None

def extract_prompt_data(response_text):
    """Extract structured prompt data from Gemini's response in the new format"""
    print("Extracting prompt data from response...")
    
    prompts = []
    
    # Pattern to match "Prompt X:" followed by content until next "Prompt X:" or end
    prompt_pattern = r'Prompt\s+(\d+):\s*(.*?)(?=Prompt\s+\d+:|$)'
    matches = re.findall(prompt_pattern, response_text, re.DOTALL | re.IGNORECASE)
    
    print(f"Found {len(matches)} potential prompts using pattern matching")
    
    for prompt_num, prompt_content in matches:
        prompt_data = {
            'prompt_number': int(prompt_num),
            'prompt_title': '',
            'description': '',
            'final_combined_prompt': '',
            'negative_prompt': ''
        }
        
        content = prompt_content.strip()
        
        # Extract the title/name (first line after "Prompt X:")
        lines = content.split('\n')
        if lines:
            # First non-empty line is likely the title
            for line in lines:
                if line.strip():
                    prompt_data['prompt_title'] = line.strip()
                    break
        
        # Extract description (text before "Final Combined Prompt:")
        desc_pattern = r'^(.*?)(?=Final\s+Combined\s+Prompt:|$)'
        desc_match = re.search(desc_pattern, content, re.DOTALL | re.IGNORECASE)
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove the title from description if it's included
            if prompt_data['prompt_title']:
                description = description.replace(prompt_data['prompt_title'], '').strip()
            prompt_data['description'] = description
        
        # Extract Final Combined Prompt
        final_prompt_pattern = r'Final\s+Combined\s+Prompt:\s*(.*?)(?=Negative\s+Prompt:|$)'
        final_match = re.search(final_prompt_pattern, content, re.DOTALL | re.IGNORECASE)
        if final_match:
            prompt_data['final_combined_prompt'] = final_match.group(1).strip()
        
        # Extract Negative Prompt
        negative_pattern = r'Negative\s+Prompt:\s*(.*?)(?=Prompt\s+\d+:|$)'
        negative_match = re.search(negative_pattern, content, re.DOTALL | re.IGNORECASE)
        if negative_match:
            prompt_data['negative_prompt'] = negative_match.group(1).strip()
        
        # Clean up extracted text
        for key in prompt_data:
            if isinstance(prompt_data[key], str):
                # Remove extra whitespace and clean up
                prompt_data[key] = re.sub(r'\s+', ' ', prompt_data[key]).strip()
                # Remove trailing punctuation from titles
                if key == 'prompt_title':
                    prompt_data[key] = prompt_data[key].rstrip('.,!?:')
        
        # Only add prompt if it has meaningful content
        if prompt_data['final_combined_prompt'] or prompt_data['prompt_title']:
            prompts.append(prompt_data)
            print(f"Extracted Prompt {prompt_data['prompt_number']}: {prompt_data['prompt_title']}")
    
    print(f"Successfully extracted {len(prompts)} prompts from response.")
    return prompts

def save_prompt_data(prompts, title="prompts"):
    """Save prompt data to JSON file"""
    timestamp = int(time.time())
    filename = f"{title}_prompts_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)
    
    print(f"Prompt data saved to: {filepath}")
    return filepath

# Add a helper function to clean up the STORY_TEXT configuration
# This removes the need to edit the story prompt format since we're reading existing responses

def get_story_title_for_filename():
    """Get a clean title for filename generation"""
    title = STORY_TITLE.strip()
    if not title:
        # Try to derive from current timestamp if no title
        title = f"prompts_{int(time.time())}"
    
    # Clean title for filename
    title = re.sub(r'[^\w\s-]', '', title).strip()
    title = re.sub(r'[-\s]+', '_', title)
    return title

def send_request_to_gemini(driver, wait, request_text):
    """Send a new request to Gemini and wait for response"""
    print("Sending new request to Gemini...")
    
    try:
        # Look for the input field/textarea
        input_selectors = [
            "textarea[placeholder*='Enter a prompt']",
            "textarea[placeholder*='Message']", 
            ".ql-editor",
            "[contenteditable='true']",
            "textarea",
            ".input-field",
            ".prompt-textarea"
        ]
        
        input_element = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        input_element = element
                        print(f"Found input using selector: {selector}")
                        break
                if input_element:
                    break
            except:
                continue
        
        if not input_element:
            print("❌ Could not find input field. Please make sure you're on the Gemini chat page.")
            return False
        
        # Clear any existing text and send the request
        input_element.click()
        time.sleep(1)
        
        # Clear existing content
        input_element.clear()
        time.sleep(0.5)
        
        # Type the request
        print("Typing the request...")
        input_element.send_keys(request_text)
        time.sleep(2)
        
        # Send the message (try Enter or look for send button)
        print("Sending the request...")
        try:
            input_element.send_keys(Keys.RETURN)
        except:
            # Try to find and click send button
            send_selectors = [
                "[aria-label*='Send']",
                "button[type='submit']",
                ".send-button",
                "[data-testid*='send']"
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    send_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if send_button.is_displayed():
                        send_button.click()
                        break
                except:
                    continue
        
        print("✅ Request sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error sending request: {e}")
        return False

def wait_for_gemini_response(driver, wait, timeout_seconds=150):
    """Wait for Gemini to generate a response"""
    print(f"Waiting for Gemini response (timeout: {timeout_seconds} seconds)...")
    
    start_time = time.time()
    last_length = 0
    stable_count = 0
    
    while time.time() - start_time < timeout_seconds:
        try:
            # Check for response content
            response_text = read_latest_gemini_response(driver, wait)
            
            if response_text:
                current_length = len(response_text)
                
                # Check if response is growing (being generated)
                if current_length > last_length:
                    last_length = current_length
                    stable_count = 0
                    print(f"Response growing... ({current_length} characters)")
                else:
                    stable_count += 1
                    
                # If response has been stable for 3 checks (15 seconds), consider it complete
                if stable_count >= 3 and current_length > 500:
                    print(f"✅ Response appears complete ({current_length} characters)")
                    return response_text
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error while waiting: {e}")
            time.sleep(5)
    
    print(f"⚠️ Timeout reached ({timeout_seconds}s). Attempting to read current response...")
    return read_latest_gemini_response(driver, wait)

def main():
    # Use request from script configuration
    print("=== Gemini Prompt Extractor ===")
    print("This script can either:")
    print("1. Read the latest response from your current Gemini conversation")
    print("2. Send a new request and wait for Gemini's response")
    print("\nExpected format: 'Prompt X:', 'Final Combined Prompt:', 'Negative Prompt:'")
    
    # Ask user what they want to do
    print("\nChoose an option:")
    print("1. Read existing response from current conversation")
    print("2. Send new request and wait for response")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    send_new_request = (choice == '2')
    
    # Use title from configuration for filename
    title = get_story_title_for_filename()
    
    print(f"\nProcessing conversation for: '{title}'")
    
    if send_new_request:
        print(f"\nRequest to be sent:")
        print("-" * 50)
        print(STORY_TEXT[:200] + "..." if len(STORY_TEXT) > 200 else STORY_TEXT)
        print("-" * 50)
        
        confirm = input("\nSend this request to Gemini? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return
    
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    
    # Start browser
    print("\nStarting browser...")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # Navigate to Gemini
        print("Navigating to Gemini...")
        driver.get("https://gemini.google.com/app/400d09ad179f3ad0")
        time.sleep(3)
        
        # Handle authentication if needed
        authenticate_google(driver, wait)
        
        # Wait for page to load
        print("Waiting for Gemini interface to load...")
        time.sleep(5)
        
        response_text = None
        
        if send_new_request:
            print("\n" + "="*60)
            print("SENDING NEW REQUEST TO GEMINI")
            print("="*60)
            
            # Send the request
            if send_request_to_gemini(driver, wait, STORY_TEXT):
                # Wait for response
                response_text = wait_for_gemini_response(driver, wait, timeout_seconds=150)
            else:
                print("❌ Failed to send request to Gemini")
                return
        else:
            print("\n" + "="*60)
            print("READING EXISTING RESPONSE FROM CONVERSATION")
            print("="*60)
            print("The script will now read the latest response that's already")
            print("displayed in your Gemini conversation.")
            print("Make sure you have already asked Gemini to create prompts!")
            print("Expected format: 'Prompt X:', 'Final Combined Prompt:', 'Negative Prompt:'")
            print("="*60)
            
            # Read the latest response from the page
            response_text = read_latest_gemini_response(driver, wait)
        
        if response_text:
            print("✅ Response found! Processing prompt data...")
            
            # Save raw response for debugging
            raw_response_file = os.path.join(OUTPUT_DIR, f"{title}_raw_response_{int(time.time())}.txt")
            with open(raw_response_file, 'w', encoding='utf-8') as f:
                f.write("=== EXTRACTED RESPONSE ===\n")
                f.write(f"Extracted at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Title: {title}\n")
                f.write("="*50 + "\n\n")
                f.write(response_text)
            print(f"Raw response saved to: {raw_response_file}")
            
            # Extract prompt data
            prompts = extract_prompt_data(response_text)
            
            if prompts:
                # Save structured prompt data
                prompt_file = save_prompt_data(prompts, title)
                
                print(f"\n" + "="*50)
                print("SUCCESS!")
                print("="*50)
                print(f"✅ Extracted {len(prompts)} prompts from the response!")
                print(f"📄 Prompt data saved to: {prompt_file}")
                print(f"📝 Raw response saved to: {raw_response_file}")
                
                # Print summary
                print(f"\n📋 PROMPT SUMMARY:")
                print("-" * 30)
                for prompt in prompts:
                    print(f"Prompt {prompt['prompt_number']}: {prompt['prompt_title']}")
                print("-" * 30)
                print(f"Total prompts: {len(prompts)}")
                
            else:
                print("\n❌ No prompts could be extracted from the response.")
                print("💡 Possible reasons:")
                print("   - The response doesn't contain prompt breakdowns")
                print("   - The format is different than expected")
                print("   - You may need to ask Gemini to create prompts in the expected format first")
                print(f"📝 Check the raw response file for debugging: {raw_response_file}")
        else:
            print("\n❌ No response found on the page.")
            print("💡 Make sure you:")
            print("   1. Have already sent your request to Gemini")
            print("   2. Received a response with prompt breakdowns in the format:")
            print("      'Prompt 1:', 'Final Combined Prompt:', 'Negative Prompt:'")
            print("   3. Are on the correct Gemini conversation page")
            
        print(f"\nKeeping browser open for 30 seconds so you can view the results...")
        print("You can close this manually or wait for auto-close.")
        time.sleep(30)
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        # Take screenshot for debugging
        debug_screenshot = os.path.join(OUTPUT_DIR, f"debug_error_{int(time.time())}.png")
        try:
            driver.save_screenshot(debug_screenshot)
            print(f"Debug screenshot saved to: {debug_screenshot}")
        except:
            pass
        
    finally:
        print("\n🔄 Closing browser...")
        driver.quit()
        print("✅ Done!")

if __name__ == "__main__":
    main()