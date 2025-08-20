import json
import os
import time
import subprocess
import tempfile
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data_wall")
GENERATED_IMAGES_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "prompt_images")
IMAGE_GENERATION_SCRIPT = "perplexity_automation.py"

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

def find_latest_prompt_file():
    """Find the most recent prompt data JSON file"""
    prompt_files = []
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"❌ Prompt data directory not found: {OUTPUT_DIR}")
        return None
    
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith('.json') and 'prompts' in file:
            filepath = os.path.join(OUTPUT_DIR, file)
            prompt_files.append((filepath, os.path.getmtime(filepath)))
    
    if not prompt_files:
        print(f"❌ No prompt JSON files found in {OUTPUT_DIR}")
        return None
    
    # Return the most recent file
    latest_file = max(prompt_files, key=lambda x: x[1])[0]
    print(f"📋 Found {len(prompt_files)} prompt file(s), using latest: {os.path.basename(latest_file)}")
    return latest_file

def load_prompt_data(filepath):
    """Load prompt data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading prompt data: {e}")
        return None

def display_prompt_preview(prompt_data):
    """Display a preview of the prompt components"""
    print("📝 Prompt Components:")
    
    if prompt_data.get('description'):
        desc = prompt_data['description']
        print(f"   📖 Description: {desc[:100]}{'...' if len(desc) > 100 else ''}")
    
    if prompt_data.get('final_combined_prompt'):
        main_prompt = prompt_data['final_combined_prompt']
        print(f"   🎨 Main Prompt: {main_prompt[:150]}{'...' if len(main_prompt) > 150 else ''}")
    
    if prompt_data.get('negative_prompt'):
        neg_prompt = prompt_data['negative_prompt']
        print(f"   ❌ Negative Prompt: {neg_prompt[:100]}{'...' if len(neg_prompt) > 100 else ''}")
    
    print()

def create_image_generation_prompt(prompt_data):
    """Create a comprehensive image generation prompt from prompt data"""
    prompt_parts = []
    
    # Add description if available
    if prompt_data.get('description'):
        prompt_parts.append(f"Description: {prompt_data['description']}")
    
    # Add the main final_combined_prompt
    if prompt_data.get('final_combined_prompt'):
        prompt_parts.append(prompt_data['final_combined_prompt'])
    
    # Add negative prompt information (as a comment for reference)
    if prompt_data.get('negative_prompt'):
        prompt_parts.append(f"Negative Prompt (avoid these): {prompt_data['negative_prompt']}")
    
    # Fallback: combine available elements if no final_combined_prompt
    if not prompt_data.get('final_combined_prompt'):
        if prompt_data.get('prompt_title'):
            prompt_parts.append(prompt_data['prompt_title'])
    
    # Join all parts
    if prompt_parts:
        full_prompt = ". ".join(prompt_parts)
        return full_prompt.strip()
    
    return "Generate an image based on the provided prompt data"

def create_modified_image_script(original_script_path, prompt_data, prompt_number, prompt_title):
    """Create a temporary JSON file with current prompt data for perplexity_automation.py to read"""
    
    # Create comprehensive prompt from all available data
    prompt_parts = []
    
    # Add description as context
    if prompt_data.get('description'):
        prompt_parts.append(f"Context: {prompt_data['description']}")
    
    # Add the main prompt
    if prompt_data.get('final_combined_prompt'):
        prompt_parts.append(prompt_data['final_combined_prompt'])
    
    # Add negative prompt guidance
    if prompt_data.get('negative_prompt'):
        prompt_parts.append(f"Important: Avoid these elements: {prompt_data['negative_prompt']}")
    
    # Combine all parts
    full_prompt = ". ".join(prompt_parts) if prompt_parts else "Generate an image"
    
    # Create a current prompt data file that perplexity_automation.py can read
    current_prompt_data = {
        "current_prompt": full_prompt,
        "prompt_number": prompt_number,
        "prompt_title": prompt_title,
        "timestamp": time.time(),
        "original_data": prompt_data
    }
    
    # Save to a current prompt file
    current_prompt_file = os.path.join(OUTPUT_DIR, "current_prompt.json")
    with open(current_prompt_file, 'w', encoding='utf-8') as f:
        json.dump(current_prompt_data, f, indent=2, ensure_ascii=False)
    
    print(f"📝 Created current prompt file: {current_prompt_file}")
    print(f"✅ Prompt preview: {full_prompt[:100]}...")
    
    # Create prompt-specific download directory with shorter name
    # Clean and truncate the title to avoid filesystem limits
    clean_title = prompt_title.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace(':', '').replace('?', '').replace('!', '').replace("'", "").replace('"', '').replace('\\', '').replace('*', '').replace('<', '').replace('>', '').replace('|', '')
    
    # Truncate title to max 50 characters to avoid long filenames
    if len(clean_title) > 50:
        clean_title = clean_title[:50]
    
    prompt_folder = f"prompt_{prompt_number:02d}_{clean_title}"
    prompt_download_dir = os.path.join(GENERATED_IMAGES_DIR, prompt_folder)
    
    try:
        os.makedirs(prompt_download_dir, exist_ok=True)
        print(f"📁 Created download directory: {prompt_folder}")
    except OSError as e:
        # If still too long, use just the prompt number
        print(f"⚠️ Folder name still too long, using shorter name: {e}")
        prompt_folder = f"prompt_{prompt_number:02d}"
        prompt_download_dir = os.path.join(GENERATED_IMAGES_DIR, prompt_folder)
        os.makedirs(prompt_download_dir, exist_ok=True)
        print(f"📁 Created simplified download directory: {prompt_folder}")
    
    # Return the original script path (no modification needed) and download directory
    return original_script_path, prompt_download_dir

def verify_image_download(download_dir, prompt_number, timeout=60):
    """Verify that an image was downloaded in the specified directory"""
    print(f"🔍 Verifying image download in: {download_dir}")
    
    if not os.path.exists(download_dir):
        print(f"❌ Download directory does not exist: {download_dir}")
        return False
    
    # Get initial file list
    initial_files = set(os.listdir(download_dir))
    print(f"📁 Initial files in directory: {len(initial_files)}")
    
    # If there are already image files, consider it successful
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')
    existing_images = [f for f in initial_files if f.lower().endswith(image_extensions) and not f.endswith(('.crdownload', '.tmp', '.part'))]
    
    if existing_images:
        print(f"✅ Image files already exist! Found: {existing_images}")
        # Check file sizes and modification time to ensure they're recent
        recent_images = []
        current_time = time.time()
        
        for img_file in existing_images:
            file_path = os.path.join(download_dir, img_file)
            try:
                file_size = os.path.getsize(file_path)
                mod_time = os.path.getmtime(file_path)
                age_seconds = current_time - mod_time
                
                print(f"📊 File: {img_file} - Size: {file_size} bytes - Age: {age_seconds:.1f}s")
                
                # Consider files recent if they're less than 10 minutes old and have reasonable size
                if age_seconds < 600 and file_size > 1024:  # 10 minutes and > 1KB
                    recent_images.append(img_file)
                    
            except Exception as e:
                print(f"⚠️ Could not check file details for {img_file}: {e}")
        
        if recent_images:
            print(f"✅ Found recent image files: {recent_images}")
            return True
    
    # Wait and check for new image files
    for i in range(timeout):
        time.sleep(1)
        
        if os.path.exists(download_dir):
            current_files = set(os.listdir(download_dir))
            new_files = current_files - initial_files
            
            # Look for completed image downloads (common image extensions)
            completed_images = [f for f in new_files if f.lower().endswith(image_extensions) and not f.endswith(('.crdownload', '.tmp', '.part'))]
            
            if completed_images:
                print(f"✅ Image download verified! Found: {completed_images}")
                return True
                
            # Show progress for partial downloads
            partial_files = [f for f in new_files if f.endswith(('.crdownload', '.tmp', '.part'))]
            if partial_files and i % 10 == 0:  # Show every 10 seconds
                print(f"⏳ Download in progress... {partial_files}")
    
    print(f"❌ Image download verification failed after {timeout} seconds")
    
    # List current files for debugging
    try:
        current_files = list(os.listdir(download_dir)) if os.path.exists(download_dir) else []
        print(f"📁 Current files in directory: {current_files}")
    except:
        pass
    
    return False

def run_image_generation(script_path, prompt_number, prompt_title, download_dir):
    """Run the image generation script and verify download"""
    print(f"\n--- Generating image for Prompt {prompt_number}: {prompt_title} ---")

    try:
        # Get the Python executable path
        python_path = "python3"
        
        # Run the original script (it will read the current_prompt.json we created)
        print(f"🚀 Starting image generation for Prompt {prompt_number}...")
        result = subprocess.run([python_path, script_path], 
                              timeout=300)  # 5 minute timeout
        
        print(f"\n✅ Image generation process completed for Prompt {prompt_number}")
        print(f"Return code: {result.returncode}")
        
        # Verify that the image was actually downloaded
        if result.returncode == 0:
            print(f"🔍 Verifying image download for Prompt {prompt_number}...")
            if verify_image_download(download_dir, prompt_number, timeout=30):
                print(f"✅ Image download verified for Prompt {prompt_number}")
                return True
            else:
                print(f"❌ Image download verification failed for Prompt {prompt_number}")
                return False
        else:
            print(f"❌ Script execution failed for Prompt {prompt_number}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: Image generation for Prompt {prompt_number} took too long")
        return False
    except Exception as e:
        print(f"❌ Error running image generation for Prompt {prompt_number}: {e}")
        return False

def generate_images_from_prompts(prompts):
    """Generate images for all prompts"""
    print(f"\n=== Starting image generation for {len(prompts)} prompts ===")
    
    successful_generations = 0
    
    for i, prompt_data in enumerate(prompts):
        prompt_number = prompt_data.get('prompt_number', i + 1)
        prompt_title = prompt_data.get('prompt_title', f'Prompt {prompt_number}')
        
        print(f"\n[{i+1}/{len(prompts)}] Processing Prompt {prompt_number}: {prompt_title}")
        
        # Display detailed prompt information
        display_prompt_preview(prompt_data)
        
        # Create current prompt file for perplexity_automation.py to read
        script_path, prompt_dir = create_modified_image_script(
            IMAGE_GENERATION_SCRIPT, 
            prompt_data,  # Pass the full prompt data object
            prompt_number, 
            prompt_title
        )
        
        try:
            # Run image generation with retry logic
            retry_count = 0
            max_retries = 3
            success = False
            
            while retry_count < max_retries and not success:
                if retry_count > 0:
                    print(f"\n🔄 Retry attempt {retry_count + 1}/{max_retries} for Prompt {prompt_number}")
                
                # Run image generation (using original script, it reads current_prompt.json)
                success = run_image_generation(script_path, prompt_number, prompt_title, prompt_dir)
                
                if success:
                    successful_generations += 1
                    print(f"✓ Successfully generated and verified image for Prompt {prompt_number}")
                    print(f"  📁 Check folder: {prompt_dir}")
                    break  # Exit retry loop on success
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"⚠️ Generation/verification failed, retrying in 10 seconds...")
                        time.sleep(10)
                    else:
                        print(f"❌ All retry attempts failed for Prompt {prompt_number}")
            
            # Wait between generations to avoid overwhelming the system (only if successful)
            if success and i < len(prompts) - 1:  # Don't wait after the last prompt
                print("⏳ Waiting 30 seconds before next generation...")
                time.sleep(30)
                
        except Exception as e:
            print(f"❌ Error processing Prompt {prompt_number}: {e}")
    
    print(f"\n=== Image Generation Complete ===")
    print(f"Successfully generated: {successful_generations}/{len(prompts)} images")
    print(f"Images saved in: {GENERATED_IMAGES_DIR}")
    return successful_generations

def main():
    print("=== Automatic Prompt Image Generator ===")
    print("Automatically finding latest prompt data and generating images...")
    
    # Automatically find and use the latest prompt file
    latest_file = find_latest_prompt_file()
    
    if not latest_file:
        print("❌ No prompt files found. Please run gemini_scene_extractor.py first to generate prompt data.")
        return
    
    print(f"📄 Using latest prompt file: {os.path.basename(latest_file)}")
    
    # Load prompt data automatically
    prompts = load_prompt_data(latest_file)
    
    if not prompts:
        print("❌ Failed to load prompt data.")
        return
    
    print(f"✅ Loaded {len(prompts)} prompts:")
    for prompt in prompts:
        print(f"   Prompt {prompt.get('prompt_number', '?')}: {prompt.get('prompt_title', 'Untitled')}")
    
    # Check if image generation script exists
    if not os.path.exists(IMAGE_GENERATION_SCRIPT):
        print(f"❌ Error: {IMAGE_GENERATION_SCRIPT} not found in current directory.")
        return
    
    # Auto-confirm and start generation
    print(f"\n🚀 Auto-starting image generation for {len(prompts)} prompts...")
    print(f"⏱️  Estimated time: {len(prompts) * 3} minutes")
    print("🔥 Starting automatic generation in 3 seconds...")
    time.sleep(3)
    
    # Start image generation automatically
    successful_count = generate_images_from_prompts(prompts)
    
    print(f"\n🎉 Generation completed!")
    print(f"✅ Successfully generated {successful_count}/{len(prompts)} images")
    print(f"📁 Check output directory: {GENERATED_IMAGES_DIR}")

if __name__ == "__main__":
    main()
