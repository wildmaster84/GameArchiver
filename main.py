import csv
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import time
import re
import shutil

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
                response = requests.get(url)
                response.raise_for_status()
                with open(cache, 'wb') as file:
                    file.write(response.content)
            
                return response.text
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
    # Check if onlineLeaderboards element exists
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
    pattern = re.compile(r'screenlg\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
    banner = re.compile(r'banner\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
    boxartlg = re.compile(r'boxartlg\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
    background = re.compile(r'background\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
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
                    break  # Exit the retry loop if successful
                except requests.RequestException as e:
                    retries += 1
                    wait_time = backoff_factor * retries
                    print(f"Error downloading the image from {url}: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            else:
                # Save the default image if the download fails after retries
                print(f"Skipping {save_path} due to download failure.")

def process_file(local_file):
    with open('template.html', 'r', encoding='utf-8') as template_file:
        template = template_file.read()

    Pages_dir = Path(__file__).parent.resolve() / "Pages"
    Pages_dir.mkdir(parents=True, exist_ok=True)

    Entries = []

    with open(local_file, mode='r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            gallery = ""
            id = row['Title ID'].lower()
            dirs = Pages_dir / id.upper()
            if not dirs.exists():
                print(f"Saving: {dirs}")
                new_url = "http://marketplace-xb.xboxlive.com/marketplacecatalog/v1/product/en-US/66ACD000-77FE-1000-9115-D802{id}?bodytypes=1.3&detailview=detaillevel5&pagenum=1&pagesize=1&stores=1&tiers=2.3&offerfilter=1&producttypes=1.5.18.19.20.21.22.23.30.34.37.46.47.61"
                market_url = new_url.replace('{id}', id)
                xml_data = fetch_xml_from_url(market_url, id)
                if xml_data:
                    fields = get_fields_from_xml(xml_data)
                    pattern = re.compile(r'screenlg\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
                    save_images(fields['imageUrls'], dirs, f'{Pages_dir}/00000000')
                    for imgUrl in fields['imageUrls']:
                        image_name = imgUrl.split("/")[-1]
                        if pattern.search(image_name):
                            if image_name not in gallery:
                                gallery += f'<div class="gallery-item"><img src="./{image_name}" alt="image"></div>'
                    GameEntry = f"## ![](./tile.png) [{fields['title']}](Pages/{id}/index.html)"
                    Entries.append((fields['title'], GameEntry))
                    content = template.replace('{title}', fields["title"])
                    content = content.replace('{id}', id)
                    content = content.replace('{market_url}', market_url)
                    content = content.replace('{description}', fields["description"])
                    content = content.replace('{developerName}', fields["developerName"])
                    content = content.replace('{releaseDate}', fields["releaseDate"])
                    content = content.replace('{publisherName}', fields["publisherName"])
                    content = content.replace('{capabilities}', fields["capabilities"])
                    content = content.replace('{gallery}', gallery)
                    filename = dirs / "index.html"
                    with open(filename, mode='w+', encoding='utf-8') as file:
                        file.write(content)
            else:
                print(f"Skipping: {dirs}")
    with open("Home.md", "w") as home_file:
        sorted_titles_and_values = sorted(Entries, key=lambda x: x[0].lower())
        for title, entry in sorted_titles_and_values:
            home_file.write(entry + "\n")

try:
    process_file('Games.csv')
except Exception as e:
    print(e)
