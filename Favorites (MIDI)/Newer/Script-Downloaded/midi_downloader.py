#!/usr/bin/env python3
"""
MIDI File Downloader Script

This script reads download links from midi_links.txt and downloads
all the files to a specified folder using Selenium to automate browser interactions.
It enables and clicks download buttons just like the Tampermonkey script.
"""

import os
import sys
import time
from urllib.parse import urlparse, unquote
from pathlib import Path
import logging
from datetime import datetime
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class MidiDownloader:
    def __init__(self, links_file="midi_links.txt", download_folder="downloads"):
        self.links_file = Path(links_file)
        self.download_folder = Path(download_folder)
        self.failed_downloads = []
        self.successful_downloads = []
        self.driver = None
        
        # Create download folder if it doesn't exist
        self.download_folder.mkdir(exist_ok=True)
        
        # Set up logging
        log_file = self.download_folder / "download_log.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Set up Chrome WebDriver with download preferences"""
        chrome_options = Options()
        
        # Set download directory
        prefs = {
            "download.default_directory": str(self.download_folder.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Optional: Run headless (remove this line if you want to see the browser)
        # chrome_options.add_argument("--headless")
        
        # Disable unnecessary features for better performance
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Chrome WebDriver initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            self.logger.error("Make sure Chrome and ChromeDriver are installed")
            return False

    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed")

    def read_links(self):
        """Read all links from the links file"""
        if not self.links_file.exists():
            self.logger.error(f"Links file not found: {self.links_file}")
            return []
        
        with open(self.links_file, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        
        self.logger.info(f"Found {len(links)} links to process")
        return links

    def get_initial_file_count(self):
        """Get the current number of files in download directory"""
        return len(list(self.download_folder.glob("*")))

    def wait_for_download(self, initial_count, timeout=30):
        """Wait for a new file to appear in the download directory"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_count = self.get_initial_file_count()
            
            # Check for .crdownload files (Chrome partial downloads)
            crdownload_files = list(self.download_folder.glob("*.crdownload"))
            
            if current_count > initial_count and not crdownload_files:
                # New file appeared and no partial downloads
                return True
            
            time.sleep(0.5)
        
        return False

    def enable_and_click_download_button(self, url, max_retries=3):
        """Navigate to URL and click the download button, similar to Tampermonkey script"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempting to download from: {url} (attempt {attempt + 1})")
                
                # Get initial file count
                initial_file_count = self.get_initial_file_count()
                
                # Navigate to the URL
                self.driver.get(url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Try to find and enable the download button
                try:
                    # Wait for the download button to be present
                    download_btn = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "btnDownload"))
                    )
                    
                    # Enable the button if it's disabled (similar to Tampermonkey script)
                    if download_btn.get_attribute("disabled"):
                        self.driver.execute_script("arguments[0].removeAttribute('disabled');", download_btn)
                        self.driver.execute_script("arguments[0].classList.remove('aspNetDisabled');", download_btn)
                        self.logger.info("Download button enabled")
                    
                    # Click the download button
                    download_btn.click()
                    self.logger.info("Download button clicked")
                    
                    # Wait for download to complete
                    if self.wait_for_download(initial_file_count, timeout=30):
                        self.logger.info("Download completed successfully")
                        self.successful_downloads.append((url, "Downloaded"))
                        return True
                    else:
                        self.logger.warning("Download timeout or failed")
                        self.failed_downloads.append((url, "Download timeout"))
                        return False
                        
                except TimeoutException:
                    self.logger.warning(f"Download button not found on {url}")
                    self.failed_downloads.append((url, "Download button not found"))
                    return False
                except NoSuchElementException:
                    self.logger.warning(f"Download button element not found on {url}")
                    self.failed_downloads.append((url, "Download button element not found"))
                    return False
                    
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Failed to download {url} after {max_retries} attempts")
                    self.failed_downloads.append((url, str(e)))
                    return False

    def download_all(self, delay_between_downloads=1):
        """Download all files from the links using Selenium"""
        links = self.read_links()
        if not links:
            self.logger.error("No links found to download")
            return
        
        # Set up the WebDriver
        if not self.setup_driver():
            self.logger.error("Failed to set up WebDriver. Exiting.")
            return
        
        try:
            start_time = time.time()
            self.logger.info(f"Starting download of {len(links)} files...")
            self.logger.info(f"Download folder: {self.download_folder.absolute()}")
            
            for i, url in enumerate(links, 1):
                self.logger.info(f"Processing {i}/{len(links)}: {url}")
                
                self.enable_and_click_download_button(url)
                
                # Add delay between downloads to be respectful to the server
                if i < len(links):  # Don't delay after the last download
                    time.sleep(delay_between_downloads)
            
            # Generate summary
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.info("\n" + "="*50)
            self.logger.info("DOWNLOAD SUMMARY")
            self.logger.info("="*50)
            self.logger.info(f"Total links processed: {len(links)}")
            self.logger.info(f"Successful downloads: {len(self.successful_downloads)}")
            self.logger.info(f"Failed downloads: {len(self.failed_downloads)}")
            self.logger.info(f"Total time: {duration:.2f} seconds")
            self.logger.info(f"Average time per file: {duration/len(links):.2f} seconds")
            
            if self.failed_downloads:
                self.logger.info("\nFailed downloads:")
                for url, error in self.failed_downloads:
                    self.logger.info(f"  {url}: {error}")
                
                # Save failed downloads to a file for retry
                failed_file = self.download_folder / "failed_downloads.txt"
                with open(failed_file, 'w') as f:
                    for url, error in self.failed_downloads:
                        f.write(f"{url}\n")
                self.logger.info(f"\nFailed URLs saved to: {failed_file}")
        
        finally:
            # Always close the driver
            self.close_driver()

def main():
    """Main function"""
    print("MIDI File Downloader")
    print("="*30)
    
    # Check if links file exists
    links_file = Path("midi_links.txt")
    if not links_file.exists():
        print(f"Error: {links_file} not found!")
        print("Please make sure the midi_links.txt file is in the same directory as this script.")
        input("Press Enter to exit...")
        return
    
    # Get user preferences
    download_folder = input("Enter download folder name (default: 'downloads'): ").strip()
    if not download_folder:
        download_folder = "downloads"
    
    delay = input("Enter delay between downloads in seconds (default: 1): ").strip()
    try:
        delay = float(delay) if delay else 1.0
    except ValueError:
        delay = 1.0
    
    print(f"\nConfiguration:")
    print(f"  Links file: {links_file}")
    print(f"  Download folder: {download_folder}")
    print(f"  Delay between downloads: {delay} seconds")
    
    confirm = input("\nProceed with download? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Download cancelled.")
        return
    
    # Start the download process
    downloader = MidiDownloader(links_file, download_folder)
    downloader.download_all(delay)
    
    print("\nDownload process completed!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()