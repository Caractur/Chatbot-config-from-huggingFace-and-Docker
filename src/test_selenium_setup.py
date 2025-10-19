import os
import sys

def test_selenium_import():
    """Test if Selenium can be imported"""
    try:
        from selenium import webdriver
        print("✓ Selenium imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Selenium import failed: {e}")
        return False

def test_chromedriver_path():
    """Test if ChromeDriver can be found"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        # Try to create Chrome driver
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        print("✓ ChromeDriver found and working")
        driver.quit()
        return True
        
    except Exception as e:
        print(f"✗ ChromeDriver test failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Chrome is installed")
        print("2. Download ChromeDriver from: https://chromedriver.chromium.org/")
        print("3. Place chromedriver.exe in this folder or add to PATH")
        return False

def test_simple_crawl():
    """Test a simple crawl to verify everything works"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("\nTesting simple crawl...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Test with a simple website
        test_url = "https://www.htu.edu.jo/"
        print(f"Testing with: {test_url}")
        
        driver.get(test_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a bit more for JavaScript
        import time
        time.sleep(3)
        
        # Get title
        title = driver.title
        print(f"Page title: {title}")
        
        # Get some text content
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"Body text length: {len(body_text)} characters")
        
        if len(body_text) > 100:
            print("✓ Successfully extracted content!")
            print(f"Preview: {body_text[:200]}...")
        else:
            print("⚠ Content seems minimal (this is expected for SPAs)")
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"✗ Simple crawl test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Selenium Setup Test")
    print("=" * 30)
    
    # Test 1: Import
    if not test_selenium_import():
        print("\nPlease install Selenium first:")
        print("pip install selenium")
        return
    
    # Test 2: ChromeDriver
    if not test_chromedriver_path():
        return
    
    # Test 3: Simple crawl
    if test_simple_crawl():
        print("\n🎉 All tests passed! Selenium is ready to use.")
        print("\nYou can now run the full crawler:")
        print("python selenium_crawler.py")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
