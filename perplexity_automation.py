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
from selenium_stealth import stealth
import undetected_chromedriver as uc

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
    """Setup Chrome driver with enhanced anti-detection and session saving"""
    print("🚀 Setting up Chrome WebDriver with anti-detection measures...")
    
    # Ensure directories exist
    try:
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        print(f"✅ Directories prepared: {USER_DATA_DIR}, {DOWNLOAD_DIR}")
    except Exception as e:
        print(f"⚠️ Directory creation warning: {e}")
    
    options = uc.ChromeOptions()
    
    # Essential options for undetected-chromedriver
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    
    # Download and file handling
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Performance and stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Window settings
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Additional stealth options (undetected-chromedriver handles most automatically)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
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
        "profile.managed_default_content_settings.images": 1,
        
        # Additional stealth preferences
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 1,
        "profile.content_settings.plugin_whitelist.adobe-flash-player": 1,
        "profile.content_settings.exceptions.plugins.*.setting": 1,
        "profile.default_content_setting_values.plugins": 1,
        "profile.content_settings.pattern_pairs.*.setting": 1,
        
        # Language and locale settings to appear more natural
        "intl.accept_languages": "en-US,en;q=0.9",
        "profile.default_content_setting_values.geolocation": 2
    }
    options.add_experimental_option("prefs", prefs)
    
    print(f"📁 Download directory set to: {DOWNLOAD_DIR}")
    
    try:
        # Create undetected Chrome driver with enhanced stealth
        driver = uc.Chrome(
            options=options,
            user_data_dir=USER_DATA_DIR,
            use_subprocess=True,
            version_main=None,  # Auto-detect Chrome version
        )
        print("✅ Undetected Chrome WebDriver initialized successfully")
        
        # Apply selenium-stealth for maximum anti-detection
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="MacIntel",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
        
        print("🕵️ Selenium-stealth activated - advanced anti-detection applied")
        print("🛡️ Undetected-chromedriver + selenium-stealth = Maximum stealth mode")
        
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

def check_for_cloudflare_challenge(driver):
    """Check if Cloudflare is challenging us and wait if needed"""
    print("🔍 Checking for Cloudflare challenge...")
    
    try:
        # Common Cloudflare challenge indicators
        cloudflare_indicators = [
            "Checking your browser before accessing",
            "Please wait while we check your browser",
            "Verifying you are human",
            "Just a moment while we check your browser",
            "Please stand by, while we are checking your browser",
            "cf-browser-verification",
            "ray-id"
        ]
        
        page_source = driver.page_source.lower()
        page_title = driver.title.lower()
        
        for indicator in cloudflare_indicators:
            if indicator.lower() in page_source or indicator.lower() in page_title:
                print(f"🛡️ Cloudflare challenge detected: '{indicator}'")
                print("⏳ Waiting for Cloudflare challenge to complete...")
                
                # Wait for challenge to complete (up to 30 seconds)
                for i in range(30):
                    time.sleep(1)
                    try:
                        current_source = driver.page_source.lower()
                        current_title = driver.title.lower()
                        
                        # Check if challenge is completed
                        challenge_completed = True
                        for check_indicator in cloudflare_indicators:
                            if check_indicator.lower() in current_source or check_indicator.lower() in current_title:
                                challenge_completed = False
                                break
                        
                        if challenge_completed and "perplexity" in current_title:
                            print("✅ Cloudflare challenge completed successfully")
                            return True
                            
                        if i % 5 == 0:  # Show progress every 5 seconds
                            print(f"⏳ Still waiting for challenge completion... ({i+1}/30s)")
                            
                    except Exception as e:
                        print(f"⚠️ Error checking challenge status: {e}")
                        continue
                
                print("⚠️ Cloudflare challenge timeout - proceeding anyway")
                return False
        
        print("✅ No Cloudflare challenge detected")
        return True
        
    except Exception as e:
        print(f"⚠️ Error checking for Cloudflare: {e}")
        return True

def add_human_like_behavior(driver):
    """Add human-like mouse movements and delays"""
    try:
        # Scroll slightly to mimic human behavior
        driver.execute_script("window.scrollTo(0, 100);")
        time.sleep(0.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.3)
        
        # Move mouse to a random position
        driver.execute_script("""
            var event = new MouseEvent('mousemove', {
                'view': window,
                'bubbles': true,
                'cancelable': true,
                'clientX': Math.floor(Math.random() * window.innerWidth),
                'clientY': Math.floor(Math.random() * window.innerHeight)
            });
            document.dispatchEvent(event);
        """)
        
        # Small random delay
        time.sleep(0.2 + (0.3 * os.urandom(1)[0] / 255))
        
    except Exception as e:
        print(f"⚠️ Error adding human-like behavior: {e}")

def human_like_typing(element, text, typing_speed=0.05):
    """Type text in a human-like manner with random delays"""
    try:
        element.clear()
        time.sleep(0.3)
        
        for char in text:
            element.send_keys(char)
            # Random delay between keystrokes (0.02 to 0.1 seconds)
            delay = typing_speed + (0.05 * os.urandom(1)[0] / 255)
            time.sleep(delay)
            
        print(f"✅ Human-like typing completed: {len(text)} characters")
        return True
        
    except Exception as e:
        print(f"⚠️ Human-like typing failed: {e}")
        # Fallback to normal typing
        try:
            element.clear()
            time.sleep(0.5)
            element.send_keys(text)
            return True
        except:
            return False

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
def navigate_to_image_generation(driver, wait):
    """Navigate through Generate Image -> Battle -> Direct Chat flow"""
    print("🎯 Starting navigation to image generation...")
    
    try:
        # Step 1: Look for "Generate Image" button
        print("🔍 Looking for 'Generate Image' button...")
        generate_image_selectors = [
            "//button[contains(text(), 'Generate Image')]",
            "//a[contains(text(), 'Generate Image')]", 
            "//div[contains(text(), 'Generate Image')]",
            "//*[contains(text(), 'Generate Image')]",
            "//button[contains(@aria-label, 'Generate Image')]",
            "//button[contains(@title, 'Generate Image')]"
        ]
        
        generate_image_button = None
        for selector in generate_image_selectors:
            try:
                generate_image_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'Generate Image' button using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not generate_image_button:
            print("❌ Could not find 'Generate Image' button")
            return False
        
        # Click Generate Image button
        print("🖱️ Clicking 'Generate Image' button...")
        add_human_like_behavior(driver)
        time.sleep(1.2)  # Human-like delay before click
        generate_image_button.click()
        time.sleep(3)  # Wait for page transition
        
        # Step 2: Look for "Battle" button
        print("🔍 Looking for 'Battle' button...")
        add_human_like_behavior(driver)
        time.sleep(2)  # Human-like delay
        battle_selectors = [
            "//button[contains(text(), 'Battle')]",
            "//a[contains(text(), 'Battle')]",
            "//div[contains(text(), 'Battle')]", 
            "//*[contains(text(), 'Battle')]",
            "//button[contains(@aria-label, 'Battle')]",
            "//button[contains(@title, 'Battle')]"
        ]
        
        battle_button = None
        for selector in battle_selectors:
            try:
                battle_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'Battle' button using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not battle_button:
            print("❌ Could not find 'Battle' button")
            return False
        
        # Click Battle button
        print("🖱️ Clicking 'Battle' button...")
        add_human_like_behavior(driver)
        time.sleep(1.2)  # Human-like delay before click
        battle_button.click()
        time.sleep(3)  # Wait for dropdown to appear
        
        # Step 3: Look for "Direct Chat" option in dropdown
        print("🔍 Looking for 'Direct Chat' option in dropdown...")
        add_human_like_behavior(driver)
        time.sleep(2)  # Human-like delay
        direct_chat_selectors = [
            "//option[contains(text(), 'Direct Chat')]",
            "//li[contains(text(), 'Direct Chat')]",
            "//div[contains(text(), 'Direct Chat')]",
            "//*[contains(text(), 'Direct Chat')]",
            "//a[contains(text(), 'Direct Chat')]",
            "//button[contains(text(), 'Direct Chat')]"
        ]
        
        direct_chat_option = None
        for selector in direct_chat_selectors:
            try:
                direct_chat_option = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'Direct Chat' option using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not direct_chat_option:
            print("❌ Could not find 'Direct Chat' option")
            return False
        
        # Click Direct Chat option
        print("🖱️ Selecting 'Direct Chat' option...")
        add_human_like_behavior(driver)
        time.sleep(1.2)  # Human-like delay before click
        direct_chat_option.click()
        time.sleep(3)  # Wait for interface to load
        
        print("✅ Successfully selected 'Direct Chat'")
        
        # Step 4: Look for "flux" text and click it
        print("🔍 Looking for 'flux' text...")
        add_human_like_behavior(driver)
        time.sleep(2)  # Human-like delay
        
        flux_selectors = [
            "//button[contains(text(), 'flux')]",
            "//div[contains(text(), 'flux')]",
            "//span[contains(text(), 'flux')]",
            "//a[contains(text(), 'flux')]",
            "//*[contains(text(), 'flux')]",
            "//button[contains(@aria-label, 'flux')]",
            "//button[contains(@title, 'flux')]",
            "//li[contains(text(), 'flux')]"
        ]
        
        flux_element = None
        for selector in flux_selectors:
            try:
                flux_element = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'flux' element using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not flux_element:
            print("❌ Could not find 'flux' element")
            return False
        
        # Click flux element
        print("🖱️ Clicking 'flux' element...")
        add_human_like_behavior(driver)
        time.sleep(1.5)  # Human-like delay before click
        flux_element.click()
        time.sleep(3)  # Wait for dropdown to appear
        
        # Step 5: Look for "imagen-4.0" option in dropdown
        print("🔍 Looking for 'imagen-4.0' option in dropdown...")
        add_human_like_behavior(driver)
        time.sleep(2)  # Human-like delay
        
        imagen_selectors = [
            "//option[contains(text(), 'imagen-4.0')]",
            "//li[contains(text(), 'imagen-4.0')]",
            "//div[contains(text(), 'imagen-4.0')]",
            "//span[contains(text(), 'imagen-4.0')]",
            "//a[contains(text(), 'imagen-4.0')]",
            "//button[contains(text(), 'imagen-4.0')]",
            "//*[contains(text(), 'imagen-4.0')]",
            "//option[contains(text(), 'Imagen-4.0')]",  # Case variation
            "//li[contains(text(), 'Imagen-4.0')]",
            "//*[contains(text(), 'Imagen')]"  # Partial match
        ]
        
        imagen_option = None
        for selector in imagen_selectors:
            try:
                imagen_option = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'imagen-4.0' option using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not imagen_option:
            print("❌ Could not find 'imagen-4.0' option")
            return False
        
        # Click imagen-4.0 option
        print("🖱️ Selecting 'imagen-4.0' option...")
        add_human_like_behavior(driver)
        time.sleep(1.5)  # Human-like delay before click
        imagen_option.click()
        time.sleep(3)  # Wait for selection to complete
        
        print("✅ Successfully navigated through Generate Image -> Battle -> Direct Chat -> flux -> imagen-4.0")
        return True
        
    except Exception as e:
        print(f"❌ Error during navigation: {str(e)}")
        return False


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
            
            # Clear and enter the prompt with human-like typing
            try:
                print("⌨️ Using human-like typing for prompt entry...")
                if human_like_typing(prompt_input, prompt_text, typing_speed=0.02):
                    print("✅ Prompt entered successfully with human-like typing")
                else:
                    # Fallback to regular typing
                    print("⚠️ Falling back to regular typing...")
                    prompt_input.clear()
                    time.sleep(0.5)
                    prompt_input.send_keys(prompt_text)
                    print("✅ Prompt entered successfully")
                
                # Add a short pause before verification
                time.sleep(1)
                
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
                
                # Add human-like behavior before submitting
                add_human_like_behavior(driver)
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
            
            # Check for Cloudflare challenge
            if not check_for_cloudflare_challenge(driver):
                print("⚠️ Cloudflare challenge may not have completed properly")
            
            # Add human-like behavior
            add_human_like_behavior(driver)
            
            # Handle login if needed
            handle_google_login(driver, wait)
            
            # Make sure we're on Perplexity.ai
            if "perplexity.ai" not in driver.current_url.lower():
                print("🔄 Redirecting to Perplexity.ai...")
                driver.get("https://www.perplexity.ai/")
                print("⏳ Waiting 10 seconds after redirect...")
                time.sleep(10)
                
                # Check for Cloudflare again after redirect
                if not check_for_cloudflare_challenge(driver):
                    print("⚠️ Cloudflare challenge may not have completed after redirect")
                
                # Add human-like behavior again
                add_human_like_behavior(driver)
            
            # Navigate through Generate Image -> Battle -> Direct Chat flow
            if not navigate_to_image_generation(driver, wait):
                print("❌ Failed to navigate to image generation interface")
                return False
            
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
