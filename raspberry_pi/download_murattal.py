#!/usr/bin/env python3
"""
Script to download Murattal files from everyayah.com and save them to the murattal directory.
This script downloads authentic Quran recitations from reliable sources.
"""

import os
import sys
import requests
import time
import argparse

# Directory to save Murattal files
MURATTAL_DIR = os.path.join(os.path.dirname(__file__), "murattal")

# Ensure the Murattal directory exists
if not os.path.exists(MURATTAL_DIR):
    os.makedirs(MURATTAL_DIR)

def download_file(url, filename):
    """Download a file from URL and save it to the specified filename."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB
        downloaded = 0
        
        print(f"Downloading {filename}...")
        
        with open(filename, 'wb') as file:
            for data in response.iter_content(block_size):
                file.write(data)
                downloaded += len(data)
                
                # Calculate and print progress
                done = int(50 * downloaded / total_size) if total_size > 0 else 0
                sys.stdout.write("\r[%s%s] %d%%" % ('=' * done, ' ' * (50 - done), done * 2))
                sys.stdout.flush()
        
        print(f"\nDownloaded {filename} successfully.")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)  # Remove partially downloaded file
        return False

def get_available_reciters():
    """Return a list of available reciters with their codes for everyayah.com."""
    return {
        'mishary': 'Alafasy_64kbps',
        'abdulbaset': 'AbdulSamad_64kbps_QuranExplorer.Com',
        'sudais': 'Abdurrahmaan_As-Sudais_64kbps',
        'husary': 'Husary_64kbps',
        'minshawi': 'Minshawy_Murattal_128kbps',
        'ajamy': 'ahmed_ibn_ali_al_ajamy_128kbps'
    }

def get_surah_info():
    """Return information about surahs."""
    return {
        1: {'name': 'Al-Fatiha', 'meaning': 'The Opening'},
        2: {'name': 'Al-Baqarah', 'meaning': 'The Cow'},
        36: {'name': 'Yasin', 'meaning': 'Ya Sin'},
        55: {'name': 'Ar-Rahman', 'meaning': 'The Most Merciful'},
        67: {'name': 'Al-Mulk', 'meaning': 'The Sovereignty'},
        93: {'name': 'Ad-Duha', 'meaning': 'The Morning Hours'},
        94: {'name': 'Ash-Sharh', 'meaning': 'The Relief'},
        112: {'name': 'Al-Ikhlas', 'meaning': 'The Sincerity'},
        113: {'name': 'Al-Falaq', 'meaning': 'The Daybreak'},
        114: {'name': 'An-Nas', 'meaning': 'Mankind'}
    }

def download_surah(reciter_code, surah_num, surah_info, reciter_name):
    """Download a specific surah from a specific reciter."""
    # Format surah number with leading zeros (001, 036, etc.)
    formatted_surah = str(surah_num).zfill(3)
    
    # Construct URL
    url = f"https://everyayah.com/data/{reciter_code}/{formatted_surah}001.mp3"
    
    # Create filename
    surah_name = surah_info[surah_num]['name'] if surah_num in surah_info else f"Surah_{formatted_surah}"
    filename = os.path.join(MURATTAL_DIR, f"Surah_{surah_name}_{reciter_name}.mp3")
    
    # Download the file
    return download_file(url, filename)

def main():
    parser = argparse.ArgumentParser(description='Download Murattal files from everyayah.com')
    parser.add_argument('--list-reciters', action='store_true', help='List available reciters and exit')
    parser.add_argument('--list-surahs', action='store_true', help='List available surahs and exit')
    parser.add_argument('--all', action='store_true', help='Download all configured surahs')
    
    args = parser.parse_args()
    
    # Get available reciters and surah info
    reciters = get_available_reciters()
    surah_info = get_surah_info()
    
    # If requested, list available reciters and exit
    if args.list_reciters:
        print("Available reciters:")
        for code, name in reciters.items():
            print(f" - {code} ({name})")
        return
    
    # If requested, list available surahs and exit
    if args.list_surahs:
        print("Available surahs:")
        for num, info in sorted(surah_info.items()):
            print(f" - {num}. {info['name']} ({info['meaning']})")
        return
    
    print("Starting Murattal download process...")
    
    # Default list of surahs to download
    surahs_to_download = [1, 2, 36, 55, 67, 112, 113, 114]
    
    # Default list of reciters to download from
    reciters_to_download = [
        ('mishary', 'Mishary'),
        ('abdulbaset', 'AbdulBaset')
    ]
    
    total_downloaded = 0
    for reciter_code, reciter_name in reciters_to_download:
        if reciter_code not in reciters:
            print(f"Reciter {reciter_code} not found, skipping.")
            continue
            
        print(f"\nDownloading from reciter: {reciter_name}")
        reciter_downloaded = 0
        
        for surah_num in surahs_to_download:
            if surah_num not in surah_info:
                print(f"Surah {surah_num} not found in surah info, skipping.")
                continue
                
            surah_name = surah_info[surah_num]['name']
            
            # Check if file already exists to avoid redundant downloads
            formatted_surah = str(surah_num).zfill(3)
            filename = os.path.join(MURATTAL_DIR, f"Surah_{surah_name}_{reciter_name}.mp3")
            
            if os.path.exists(filename):
                print(f"File for Surah {surah_name} by {reciter_name} already exists, skipping.")
                continue
            
            if download_surah(reciters[reciter_code], surah_num, surah_info, reciter_name):
                reciter_downloaded += 1
                total_downloaded += 1
            
            # Sleep briefly to avoid hammering the server
            time.sleep(1)
        
        print(f"Downloaded {reciter_downloaded} surahs from {reciter_name}")
    
    print(f"\nDownload complete. Total files downloaded: {total_downloaded}")
    print(f"Murattal files are located in: {MURATTAL_DIR}")
    
    # List all files in the murattal directory
    print("\nAll Murattal files:")
    for file in sorted(os.listdir(MURATTAL_DIR)):
        if file.endswith('.mp3'):
            print(f" - {file}")

if __name__ == "__main__":
    main()