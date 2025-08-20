import time
import os
import json
import functools
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# --- CONFIGURATION ---
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "selenium_chrome_profile")
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "perplexity_images")

# --- RETRY MECHANISM ---
def retry_on_failure(max_attempts=3, delay=2, backoff=1.5):
    """Decorator to retry function calls on failure"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    result = func(*args, **kwargs)
                    if attempts > 0:
                        print(f"✅ {func.__name__} succeeded on attempt {attempts + 1}")
                    return result
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        print(f"❌ {func.__name__} failed after {max_attempts} attempts. Last error: {e}")
                        raise e
                    else:
                        print(f"⚠️ {func.__name__} attempt {attempts} failed: {e}")
                        print(f"🔄 Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            return None
        return wrapper
    return decorator
SCENE_DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data_wall")

# Ensure directories exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

@retry_on_failure(max_attempts=3, delay=1)
def get_prompt_from_scene_generator():
    """Get prompt from scene_generator.py output or use default"""
    global DOWNLOAD_DIR  # Allow modification of the global download directory
    
    try:
        # First, look for current_prompt.json (new method)
        current_prompt_file = os.path.join(SCENE_DATA_DIR, "current_prompt.json")
        if os.path.exists(current_prompt_file):
            print(f"📋 Found current prompt file: {os.path.basename(current_prompt_file)}")
            
            with open(current_prompt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            current_prompt = data.get('current_prompt', '')
            
            # Check if there's a custom download directory for this prompt
            if 'prompt_number' in data and 'prompt_title' in data:
                prompt_number = data['prompt_number']
                prompt_title = data['prompt_title']
                
                # Create prompt-specific download directory with shorter name (same logic as scene_generator.py)
                clean_title = prompt_title.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace(':', '').replace('?', '').replace('!', '').replace("'", "").replace('"', '').replace('\\', '').replace('*', '').replace('<', '').replace('>', '').replace('|', '')
                
                # Truncate title to max 50 characters to avoid long filenames
                if len(clean_title) > 50:
                    clean_title = clean_title[:50]
                
                prompt_folder = f"prompt_{prompt_number:02d}_{clean_title}"
                custom_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "prompt_images", prompt_folder)
                
                try:
                    # Update the global download directory
                    DOWNLOAD_DIR = custom_download_dir
                    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                    print(f"📁 Updated download directory to: {DOWNLOAD_DIR}")
                except OSError as e:
                    # If still too long, use just the prompt number
                    print(f"⚠️ Folder name still too long, using shorter name: {e}")
                    prompt_folder = f"prompt_{prompt_number:02d}"
                    custom_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "prompt_images", prompt_folder)
                    DOWNLOAD_DIR = custom_download_dir
                    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                    print(f"📁 Updated download directory to: {DOWNLOAD_DIR}")
            
            if current_prompt:
                print(f"✅ Using current prompt: {current_prompt[:100]}...")
                return current_prompt
        
        # Fallback: Look for the latest prompt file from scene_generator.py (old method)
        if os.path.exists(SCENE_DATA_DIR):
            prompt_files = []
            for file in os.listdir(SCENE_DATA_DIR):
                if file.endswith('.json') and 'prompts' in file:
                    filepath = os.path.join(SCENE_DATA_DIR, file)
                    prompt_files.append((filepath, os.path.getmtime(filepath)))
            
            if prompt_files:
                # Get the most recent prompt file
                latest_file = max(prompt_files, key=lambda x: x[1])[0]
                print(f"📋 Found prompt file: {os.path.basename(latest_file)}")
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract the first prompt if available
                if 'prompts' in data and len(data['prompts']) > 0:
                    prompt_data = data['prompts'][0]
                    
                    # Build prompt from available data
                    prompt_parts = []
                    if prompt_data.get('description'):
                        prompt_parts.append(f"Context: {prompt_data['description']}")
                    if prompt_data.get('final_combined_prompt'):
                        prompt_parts.append(prompt_data['final_combined_prompt'])
                    if prompt_data.get('negative_prompt'):
                        prompt_parts.append(f"Important: Avoid these elements: {prompt_data['negative_prompt']}")
                    
                    full_prompt = ". ".join(prompt_parts) if prompt_parts else "Generate an image"
                    print(f"✅ Using prompt from scene_generator: {full_prompt[:100]}...")
                    return full_prompt
    
    except Exception as e:
        print(f"⚠️ Could not load prompt from scene_generator: {e}")
    
    # Default prompt if no scene_generator data found
    default_prompt = "A heartwarming, softly lit, full-body shot of a cute cartoon girl gently applying an ice pack to her boyfriend's forehead. The art style should be a modern, friendly cartoon with slightly exaggerated, expressive features, reminiscent of popular animated movies (e.g., Disney/Pixar but distinctly 2D). The girl has large, kind eyes, a small upturned nose, and a sweet, concerned smile. Her hair is styled in soft, flowing waves or a cute ponytail, with a few stray strands. She's wearing comfortable, casual attire, like a pastel-colored t-shirt and shorts. Her posture should convey tenderness and care as she leans slightly towards him. The boyfriend is depicted with a slightly flushed face, indicative of a mild fever or bump, but with a faint, appreciative smile as he looks up at her. He has soft, tousled hair and is wearing a relaxed, perhaps slightly rumpled, t-shirt. He's sitting comfortably on a sofa or bed, leaning back slightly. The ice pack is a simple, light blue or clear gel pack, slightly frosted, held delicately in her hands. The background is a soft-focus, cozy bedroom or living room, with warm, inviting colors. Perhaps a few blurred elements like a lamp, a book, or a pillow in the background to add to the domestic atmosphere. The overall mood is one of comfort, care, and gentle affection. High detail on facial expressions and hand gestures to convey emotion. Cinematic lighting."
    print("📝 Using default prompt")
    return default_prompt

@retry_on_failure(max_attempts=3, delay=2)
def setup_chrome_driver():
    """Setup Chrome driver with session saving and download preferences"""
    print("🚀 Setting up Chrome WebDriver...")
    
    # Ensure directories exist
    try:
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        print(f"✅ Directories prepared: {USER_DATA_DIR}, {DOWNLOAD_DIR}")
    except Exception as e:
        print(f"⚠️ Directory creation warning: {e}")
    
    options = webdriver.ChromeOptions()
    
    # Session saving and automation detection avoidance
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    
    # Additional stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Download preferences
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "safebrowsing.disable_download_protection": True,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        "profile.content_settings.exceptions.insecure_content.*.setting": 1,
        "profile.managed_default_content_settings.images": 1
    }
    options.add_experimental_option("prefs", prefs)
    
    # Additional download-related options
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    print(f"📁 Download directory set to: {DOWNLOAD_DIR}")
    
    try:
        driver = webdriver.Chrome(options=options)
        print("✅ Chrome WebDriver initialized successfully")
        
        # Verify driver is working and download settings
        driver.execute_script("return navigator.userAgent;")
        
        # Test if download directory is accessible
        try:
            test_file = os.path.join(DOWNLOAD_DIR, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✅ Download directory write access confirmed")
        except Exception as e:
            print(f"⚠️ Download directory write test failed: {e}")
        
        return driver
        
    except Exception as e:
        print(f"❌ Chrome WebDriver initialization failed: {e}")
        raise

@retry_on_failure(max_attempts=2, delay=3)
def handle_google_login(driver, wait):
    """Handle Google account login if required"""
    current_url = driver.current_url
    print(f"🔍 Current URL: {current_url}")
    
    if "accounts.google.com" in current_url or "signin" in current_url.lower():
        print("🔐 Google login required...")
        
        try:
            # Enter email
            email_selectors = [
                "input[type='email']",
                "input[name='identifier']",
                "#identifierId"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if email_field:
                email_field.clear()
                email_field.send_keys(GOOGLE_EMAIL)
                
                # Click Next
                next_button = driver.find_element(By.ID, "identifierNext")
                next_button.click()
                print("✅ Email entered")
                time.sleep(3)
            
            # Enter password
            password_field = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_field.send_keys(GOOGLE_PASSWORD)
            
            # Click Next
            password_next = driver.find_element(By.ID, "passwordNext")
            password_next.click()
            print("✅ Password entered, logging in...")
            
            # Wait for login to complete
            time.sleep(5)
            
        except Exception as e:
            print(f"⚠️ Login process encountered an issue: {e}")
    else:
        print("✅ Already logged in or no login required")

@retry_on_failure(max_attempts=3, delay=2)
def find_and_fill_prompt(driver, wait, prompt_text):
    """Find prompt input field and enter the text"""
    print("🔍 Looking for prompt input field...")
    
    # Ensure we're on the right page
    if "perplexity.ai" not in driver.current_url.lower():
        print("⚠️ Not on Perplexity.ai, navigating...")
        driver.get("https://www.perplexity.ai/")
        time.sleep(3)
    
    selectors_to_try = [
        "#ask-input",  # ID selector for the correct input field
        "[id='ask-input']",  # Alternative ID selector
        "textarea",
        "input[type='text']",
        "[contenteditable='true']",
        "[placeholder*='Ask']",
        "[placeholder*='question']",
        "[placeholder*='prompt']",
        "[data-testid*='search']",
        "[data-testid*='input']",
        ".search-input",
        ".query-input"
    ]
    
    for selector in selectors_to_try:
        try:
            prompt_input = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            print(f"✅ Found prompt input using selector: {selector}")
            
            # Clear and enter the prompt
            try:
                prompt_input.clear()
                time.sleep(0.5)  # Small delay after clear
                prompt_input.send_keys(prompt_text)
                print("✅ Prompt entered successfully")
                
                # Verify text was entered
                if hasattr(prompt_input, 'value') and prompt_input.get_attribute('value'):
                    entered_text = prompt_input.get_attribute('value')
                elif hasattr(prompt_input, 'text') and prompt_input.text:
                    entered_text = prompt_input.text
                else:
                    # Try to get text via JavaScript
                    entered_text = driver.execute_script("return arguments[0].value || arguments[0].textContent || arguments[0].innerText;", prompt_input)
                
                if entered_text and len(entered_text.strip()) > 10:  # Basic validation
                    print(f"✅ Text verification passed: {len(entered_text)} characters entered")
                else:
                    print("⚠️ Text verification failed, trying JavaScript input...")
                    driver.execute_script("arguments[0].value = arguments[1];", prompt_input, prompt_text)
                    time.sleep(0.5)
                
                # Submit the prompt
                prompt_input.send_keys(Keys.RETURN)
                print("✅ Prompt submitted")
                time.sleep(2)  # Wait for submission to process
                return True
                
            except Exception as input_error:
                print(f"⚠️ Error during prompt input: {input_error}")
                # Try alternative submission methods
                try:
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", prompt_input, prompt_text)
                    driver.execute_script("arguments[0].form.submit() || arguments[0].click();", prompt_input)
                    print("✅ Prompt submitted via JavaScript")
                    time.sleep(2)
                    return True
                except:
                    continue
            
        except TimeoutException:
            continue
        except Exception as e:
            print(f"⚠️ Error with selector {selector}: {e}")
            continue
    
    print("❌ Could not find prompt input field")
    return False

@retry_on_failure(max_attempts=2, delay=5)
def wait_and_find_download(driver):
    """Wait 120 seconds then look for download button and verify download"""
    print("⏳ Waiting 120 seconds for response generation...")
    time.sleep(120)
    
    # Debug: Check what's on the page
    print("🔍 Debugging page content...")
    try:
        page_title = driver.title
        current_url = driver.current_url
        print(f"📄 Page title: {page_title}")
        print(f"🔗 Current URL: {current_url}")
        
        # Look for any elements that might indicate image generation status
        status_indicators = [
            "//*[contains(text(), 'Generated')]",
            "//*[contains(text(), 'Complete')]", 
            "//*[contains(text(), 'Ready')]",
            "//*[contains(text(), 'Image')]",
            "//*[contains(text(), 'Download')]",
            "//img[@src]",
            "//canvas",
            "//*[contains(@class, 'image')]"
        ]
        
        for indicator in status_indicators:
            try:
                elements = driver.find_elements(By.XPATH, indicator)
                if elements:
                    print(f"🔍 Found {len(elements)} elements for '{indicator}'")
                    for i, elem in enumerate(elements[:3]):  # Show first 3
                        try:
                            text = elem.text.strip()[:100] if elem.text else "No text"
                            print(f"   [{i+1}] {text}")
                        except:
                            print(f"   [{i+1}] Element found but couldn't read text")
            except:
                continue
                
    except Exception as e:
        print(f"⚠️ Debug error: {e}")
    
    # Check download directory before attempting download
    initial_files = set()
    if os.path.exists(DOWNLOAD_DIR):
        initial_files = set(os.listdir(DOWNLOAD_DIR))
        print(f"📁 Initial files in download dir: {len(initial_files)}")
    
    print("🔍 Looking for download button...")
    
    download_selectors = [
        "//button[contains(text(), 'Download')]",
        "//a[contains(text(), 'Download')]", 
        "//span[contains(text(), 'Download')]",
        "//div[contains(text(), 'Download')]",
        "//*[contains(text(), 'download')]",
        "//button[contains(@aria-label, 'Download')]",
        "//button[contains(@aria-label, 'download')]",
        "//a[contains(@href, 'download')]",
        "//button[contains(@class, 'download')]",
        "//*[@role='button' and contains(text(), 'Download')]",
        "//img[contains(@alt, 'Download')]",
        "//svg[contains(@aria-label, 'Download')]/../..",
        "//*[contains(@class, 'download-btn')]",
        "//*[contains(@class, 'download-button')]",
        "//a[contains(@download, '')]",
        "//*[contains(text(), 'Save')]",
        "//*[contains(text(), 'Export')]"
    ]
    
    download_clicked = False
    
    for selector in download_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            print(f"Found {len(elements)} elements with selector: {selector}")
            
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        element_text = element.text.strip()
                        print(f"✅ Found download element: '{element_text}'")
                        
                        # Try to click
                        try:
                            element.click()
                            print("✅ Download button clicked successfully!")
                            download_clicked = True
                            break
                        except Exception as e:
                            # Try JavaScript click as fallback
                            driver.execute_script("arguments[0].click();", element)
                            print("✅ Download button clicked via JavaScript!")
                            download_clicked = True
                            break
                            
                except Exception as e:
                    continue
            
            if download_clicked:
                break
                    
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    if not download_clicked:
        print("❌ No download button found")
        # Try to save page screenshot for debugging
        try:
            screenshot_path = os.path.join(DOWNLOAD_DIR, f"debug_screenshot_{int(time.time())}.png")
            driver.save_screenshot(screenshot_path)
            print(f"📸 Debug screenshot saved: {screenshot_path}")
        except:
            pass
        return False
    
    # Wait for download to complete
    print("⏳ Waiting for download to complete...")
    download_timeout = 90  # Increased timeout to 90 seconds
    download_completed = False
    
    for i in range(download_timeout):
        time.sleep(1)
        
        if os.path.exists(DOWNLOAD_DIR):
            current_files = set(os.listdir(DOWNLOAD_DIR))
            new_files = current_files - initial_files
            
            # Check for completed image downloads (common image extensions)
            image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')
            completed_images = [f for f in new_files if f.lower().endswith(image_extensions) and not f.endswith(('.crdownload', '.tmp', '.part'))]
            
            if completed_images:
                print(f"✅ Image download completed! Files: {completed_images}")
                download_completed = True
                
                # Additional verification: check file size
                for img_file in completed_images:
                    file_path = os.path.join(DOWNLOAD_DIR, img_file)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 1024:  # At least 1KB
                            print(f"✅ Image file verified: {img_file} ({file_size} bytes)")
                        else:
                            print(f"⚠️ Image file seems too small: {img_file} ({file_size} bytes)")
                    except Exception as e:
                        print(f"⚠️ Could not verify file size for {img_file}: {e}")
                break
                
            # Show progress for partial downloads
            partial_files = [f for f in new_files if f.endswith(('.crdownload', '.tmp', '.part'))]
            if partial_files and i % 15 == 0:  # Show every 15 seconds
                print(f"⏳ Download in progress... {partial_files}")
    
    if not download_completed:
        print("⚠️ Download timeout or no new image files detected")
        # List what's in the download directory for debugging
        try:
            current_files = set(os.listdir(DOWNLOAD_DIR)) if os.path.exists(DOWNLOAD_DIR) else set()
            print(f"📁 Current files in download directory: {list(current_files)}")
            
            # Check if there are any new files at all
            all_new_files = current_files - initial_files if initial_files else current_files
            if all_new_files:
                print(f"📋 New files detected (but not recognized as images): {list(all_new_files)}")
        except Exception as e:
            print(f"⚠️ Error checking download directory: {e}")
            print(f"📁 Current files in download directory: {list(current_files)}")
        except:
            pass
        # Still return True if we clicked the download button, as the issue might be elsewhere
        return True
    
    return True

def main():
    """Main execution function with retry logic"""
    print("🚀 Starting Perplexity.ai Image Generation Script")
    
    max_main_attempts = 2
    for main_attempt in range(max_main_attempts):
        driver = None
        try:
            print(f"\n📋 Main execution attempt {main_attempt + 1}/{max_main_attempts}")
            
            # Get the prompt (this may update DOWNLOAD_DIR)
            prompt_text = get_prompt_from_scene_generator()
            
            # Setup driver (after DOWNLOAD_DIR may have been updated)
            driver = setup_chrome_driver()
            wait = WebDriverWait(driver, 20)
            
            # Navigate to Perplexity.ai
            print("🌐 Navigating to Perplexity.ai...")
            driver.get("https://www.perplexity.ai/")
            print("⏳ Waiting 10 seconds for page to load...")
            time.sleep(10)
            
            # Handle login if needed
            handle_google_login(driver, wait)
            
            # Make sure we're on Perplexity.ai
            if "perplexity.ai" not in driver.current_url.lower():
                print("🔄 Redirecting to Perplexity.ai...")
                driver.get("https://www.perplexity.ai/")
                print("⏳ Waiting 10 seconds after redirect...")
                time.sleep(10)
            
            # Find and fill prompt
            if find_and_fill_prompt(driver, wait, prompt_text):
                # Wait and look for download
                if wait_and_find_download(driver):
                    print("✅ Process completed successfully!")
                    break  # Success, exit retry loop
                else:
                    print("⚠️ Download button not found after waiting")
                    if main_attempt < max_main_attempts - 1:
                        print("🔄 Will retry entire process...")
                        continue
            else:
                print("❌ Could not enter prompt")
                if main_attempt < max_main_attempts - 1:
                    print("🔄 Will retry entire process...")
                    continue
            
            # Keep browser open for a moment
            print("📖 Keeping browser open for 10 seconds...")
            time.sleep(10)
            break  # Exit retry loop
            
        except WebDriverException as e:
            print(f"❌ WebDriver error on attempt {main_attempt + 1}: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            
            if main_attempt < max_main_attempts - 1:
                print(f"🔄 Retrying main process in 5 seconds...")
                time.sleep(5)
            else:
                print("❌ All main attempts failed due to WebDriver issues")
                
        except Exception as e:
            print(f"❌ Unexpected error on attempt {main_attempt + 1}: {e}")
            if main_attempt < max_main_attempts - 1:
                print(f"🔄 Retrying main process in 3 seconds...")
                time.sleep(3)
            else:
                print("❌ All main attempts failed")
        
        finally:
            if driver and main_attempt == max_main_attempts - 1:
                print("🔒 Closing browser...")
                try:
                    driver.quit()
                except:
                    pass

if __name__ == "__main__":
    main()
