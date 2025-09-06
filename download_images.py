#!/usr/bin/env python
"""
Script to download all images from a website and save them to static/img folder
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time


def download_images_from_site(url, output_dir="static/img"):
    """
    Download all images from a website

    Args:
        url: The website URL to download images from
        output_dir: Directory to save images to
    """

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # Send GET request to the website
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all image tags
        img_tags = soup.find_all("img")

        # Also find images in CSS background-image properties
        style_tags = soup.find_all(style=True)

        print(f"Found {len(img_tags)} image tags")

        downloaded_count = 0
        failed_count = 0

        # Download images from img tags
        for img in img_tags:
            img_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")

            if not img_url:
                continue

            # Make URL absolute
            img_url = urljoin(url, img_url)

            # Skip data URLs
            if img_url.startswith("data:"):
                continue

            try:
                # Get the image filename
                parsed_url = urlparse(img_url)
                filename = os.path.basename(parsed_url.path)

                # If no filename, generate one
                if not filename or "." not in filename:
                    filename = f"image_{downloaded_count + 1}.jpg"

                # Download the image
                print(f"Downloading: {filename}")
                img_response = requests.get(
                    img_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                img_response.raise_for_status()

                # Save the image
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_response.content)

                downloaded_count += 1
                print(f"  [OK] Saved to {filepath}")

                # Be respectful with rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  [FAIL] Failed to download {img_url}: {str(e)}")
                failed_count += 1

        # Also check for background images in inline styles
        for element in style_tags:
            style = element.get("style", "")
            if "background-image" in style:
                import re

                urls = re.findall(r'url\([\'"]?([^\'"]+)[\'"]?\)', style)
                for bg_url in urls:
                    bg_url = urljoin(url, bg_url)
                    if bg_url.startswith("data:"):
                        continue

                    try:
                        parsed_url = urlparse(bg_url)
                        filename = os.path.basename(parsed_url.path)

                        if not filename or "." not in filename:
                            filename = f"bg_image_{downloaded_count + 1}.jpg"

                        print(f"Downloading background image: {filename}")
                        img_response = requests.get(
                            bg_url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            },
                        )
                        img_response.raise_for_status()

                        filepath = os.path.join(output_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(img_response.content)

                        downloaded_count += 1
                        print(f"  [OK] Saved to {filepath}")
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"  [FAIL] Failed to download {bg_url}: {str(e)}")
                        failed_count += 1

        print(f"\n[SUCCESS] Download complete!")
        print(f"   Downloaded: {downloaded_count} images")
        print(f"   Failed: {failed_count} images")
        print(f"   Saved to: {os.path.abspath(output_dir)}")

    except Exception as e:
        print(f"[ERROR] Error accessing website: {str(e)}")
        return False

    return True


def main():
    """Main function to run the image downloader"""

    # Your website URL
    website_url = "https://store-8d46pm0wcs.mybigcommerce.com/manage/products/119/edit"

    # Output directory (relative to this script)
    output_dir = "static/img/integdental"

    print(f"Starting image download from {website_url}")
    print(f"Images will be saved to: {output_dir}")
    print("-" * 50)

    # Check if required libraries are installed
    try:
        import requests
        import bs4
    except ImportError:
        print("[ERROR] Required libraries not installed!")
        print("Please run: pip install requests beautifulsoup4")
        return

    # Download images
    success = download_images_from_site(website_url, output_dir)

    if success:
        print("\n[SUCCESS] All done! Images have been downloaded.")
    else:
        print("\n[ERROR] Download failed. Please check the error messages above.")


if __name__ == "__main__":
    main()
