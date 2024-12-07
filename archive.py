import csv
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor

# Lock for synchronizing API request timing
api_lock = threading.Lock()

def fetch_xml_from_url(url, titleId, max_retries=5, backoff_factor=1):
    cache_dir = Path(__file__).parent.resolve() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    titleId += ".xml"
    cache = Path(cache_dir) / titleId
    if not cache.exists():
        print(f"Caching : {cache}")
        retries = 0
        while retries < max_retries:
            try:
                # Ensure a delay between API requests
                with api_lock:
                    print("Waiting 3 seconds before API request...")
                    time.sleep(3)

                response = requests.get(url)
                response.raise_for_status()
                with open(cache, 'wb') as file:
                    file.write(response.content)
                
                with open(cache, 'r', encoding='utf-8') as file:
                    return file.read()
                
            except requests.RequestException as e:
                retries += 1
                wait_time = backoff_factor * retries
                print(f"Error fetching XML data: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        print(f"Failed to fetch XML data after {max_retries} attempts.")
        return None
    else:
        print(f"Loaded cache: {cache}")
        with open(cache, 'r', encoding='utf-8') as file:
            return file.read()

def get_fields_from_xml(xml):
    namespaces = {
        'a': 'http://www.w3.org/2005/Atom',
        '': 'http://marketplace.xboxlive.com/resource/product/v1'
    }

    root = ET.fromstring(xml)

    full_description = root.find('.//fullDescription', namespaces)
    full_title = root.find('.//fullTitle', namespaces)
    global_original_release_date = root.find('.//globalOriginalReleaseDate', namespaces)
    publisher_name = root.find('.//publisherName', namespaces)
    developer_name = root.find('.//developerName', namespaces)
    images = root.findall('.//image/fileUrl', namespaces)    
    full_description_text = full_description.text if full_description is not None else "N/A"
    full_title_text = full_title.text if full_title is not None else "N/A"
    global_original_release_date_text = global_original_release_date.text if global_original_release_date is not None else "N/A"
    publisher_name_text = publisher_name.text if publisher_name is not None else "N/A"
    developer_name_text = developer_name.text if developer_name is not None else "N/A"
    image_urls = [img.text for img in images] if images is not None else "N/A"
    
    gameInfo = ""
    if root.find('.//onlineMultiplayerMin', namespaces) is not None:
        gameInfo += "<th><button>Xbox Live</button></th>"
    if root.find('.//offlineSystemLinkMin', namespaces) is not None:
        gameInfo += "<th><button>SystemLink</button></th>"
    if root.find('.//onlineCoopPlayersMin', namespaces) is not None:
        gameInfo += "<th><button>Coop</button></th>"

    try:
        date_obj = datetime.strptime(global_original_release_date_text, "%Y-%m-%dT%H:%M:%S")
        formatted_date = date_obj.strftime("%m/%d/%Y")
    except ValueError:
        formatted_date = "N/A"

    return {
        'description': full_description_text,
        'title': full_title_text,
        'releaseDate': formatted_date,
        'publisherName': publisher_name_text,
        'developerName': developer_name_text,
        'imageUrls': image_urls,
        'capabilities': gameInfo
    }

def save_images(image_urls, save_dir, default_image_path, max_retries=3, backoff_factor=1):
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    for url in image_urls:
        if url.lower().endswith(valid_extensions):
            retries = 0
            while retries < max_retries:
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    image_name = url.split("/")[-1]
                    save_path = Path(save_dir) / image_name
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                    break
                except requests.RequestException as e:
                    retries += 1
                    wait_time = backoff_factor * retries
                    print(f"Error downloading the image from {url}: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

def process_row(row, pages_dir):
    id = row['Title ID'].lower()
    id_upper = row['Title ID'].upper()
    dirs = pages_dir / id_upper
    if not dirs.exists():
        print(f"Saving: {dirs}")
        new_url = "https://raw.githubusercontent.com/wildmaster84/restored-media/main/{id2}/{id}.xml"
        market_url = new_url.replace('{id}', id).replace('{id2}', id_upper)
        xml_data = fetch_xml_from_url(market_url, id)
        if xml_data:
            fields = get_fields_from_xml(xml_data)
            save_images(fields['imageUrls'], dirs, f'{pages_dir}/00000000')

def process_file_multithreaded(local_file):
    pages_dir = Path(__file__).parent.resolve() / "Pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    with open(local_file, mode='r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
    
    with ThreadPoolExecutor() as executor:
        for row in rows:
            executor.submit(process_row, row, pages_dir)

try:
    process_file_multithreaded('Games.csv')
except Exception as e:
    print(e)
