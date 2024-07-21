import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re

def chunk_array(array, chunk_size):
    for i in range(0, len(array), chunk_size):
        yield array[i:i + chunk_size]

def block_malformed_requests():
    from flask import request, abort
    try:
        if request.data and not request.data.isascii():
            abort(404)
    except Exception as e:
        print(f"Error while checking request data: {e}")
        abort(404)

def gamePages(directory):
    try:
        items = os.listdir(directory)
        for item in items:
            if os.path.isdir(os.path.join(directory, item)):
                yield item
    except Exception as e:
        print(f"Error: {e}")

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
    image_urls = [img.text for img in images] if images is not None else []

    game_info = ""
    if root.find('.//onlineMultiplayerMin', namespaces) is not None:
        game_info += "<th><button class=\"btn\">Xbox Live</button></th>"
    if root.find('.//offlineSystemLinkMin', namespaces) is not None:
        game_info += "<th><button class=\"btn\">SystemLink</button></th>"
    if root.find('.//onlineCoopPlayersMin', namespaces) is not None:
        game_info += "<th><button class=\"btn\">Coop</button></th>"

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
        'capabilities': game_info
    }

def rebuild_index(id):
    from flask import safe_join
    with open('template.html', 'r', encoding='utf-8') as template_file:
        template = template_file.read()
    
    with open(safe_join('cache', f"{id.lower()}.xml"), 'r', encoding='utf-8') as xml:
        xml_data = xml.read()
    gallery = ""
    fields = get_fields_from_xml(xml_data)
    pattern = re.compile(r'screenlg\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
    
    for imgUrl in fields['imageUrls']:
        image_name = imgUrl.split("/")[-1]
        if pattern.search(image_name):
            if image_name not in gallery:
                gallery += f'<div class="gallery-item"><img src="{id}/{image_name}" alt="image"></div>'
    
    content = template.replace('{title}', fields["title"])
    content = content.replace('{id}', id)
    content = content.replace('{description}', fields["description"])
    content = content.replace('{developerName}', fields["developerName"])
    content = content.replace('{releaseDate}', fields["releaseDate"])
    content = content.replace('{publisherName}', fields["publisherName"])
    content = content.replace('{capabilities}', fields["capabilities"])
    content = content.replace('{gallery}', gallery)
    filename = f"Pages/{id}/index.html"
    with open(filename, mode='w+', encoding='utf-8') as file:
        file.write(content)
