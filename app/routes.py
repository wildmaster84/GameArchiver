from flask import send_from_directory, render_template, abort, send_file, redirect, request
import os
from werkzeug.utils import safe_join
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re
from app import app
from app.utils import gamePages

HOME_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Pages'))
CACHE_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
DEFAULT_IMAGE_DIR = os.path.join(HOME_DIRECTORY, '00000000')

def chunk_array(array, chunk_size):
    for i in range(0, len(array), chunk_size):
        yield array[i:i + chunk_size]

def block_malformed_requests():
    try:
        # Check for non-ASCII characters in the request data
        if request.data and not request.data.isascii():
            abort(404)
    except Exception as e:
        print(f"Error while checking request data: {e}")
        abort(404)

@app.before_request
def before_request_func():
    block_malformed_requests()
    if request.path.endswith("index.html"):
        new_path = request.path[:-11]  # Remove "index.html" from the path
        return redirect(new_path)

@app.errorhandler(404)
def page_not_found(e):
    path = request.path
    parent_dir = os.path.dirname(path)
    if path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        # Extract the image name
        image_name = os.path.basename(path)
        # Serve the default image
        print(f"Missing image: {path}")
        return send_from_directory(DEFAULT_IMAGE_DIR, image_name)
    else:
        message = '{"status":"404", "error": "Requested resource could not be found"}'
        return message, 404

@app.errorhandler(500)
def internal_server_error(e):
    message = '{"status":"500", "error": "Internal server error"}'
    return message, 500

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    chunk_size = 84  # Number of directories per page
    directories = [name for name in os.listdir(HOME_DIRECTORY) if os.path.isdir(os.path.join(HOME_DIRECTORY, name))]
    paged_directories = list(chunk_array(directories, chunk_size))
    total_pages = len(paged_directories)

    if page < 1 or page > total_pages:
        page = 1  # Default to the first page if the page number is invalid

    # Get the full paths
    directories_with_paths = [(name, os.path.abspath(os.path.join(HOME_DIRECTORY, name))) for name in paged_directories[page-1]]

    return render_template(
        'home.html', 
        total=len(directories), 
        directories=directories_with_paths, 
        page=page, 
        total_pages=total_pages,
        hostname=request.host,
        max=max,
        min=min
    )

@app.route('/api')
def api_index():
    return "No index found."

@app.route('/api/xml/<path:path>')
def api_xml(path):
    safe_file_id = safe_join(CACHE_DIRECTORY, f"{path.lower()}.xml")
    if os.path.exists(safe_file_id):
        return send_file(safe_file_id, as_attachment=False, mimetype='application/xml')
    else:
        abort(404)

@app.route('/<path:path>')
def serve_file_or_directory(path):
    # Safely join the base directory with the requested path
    full_path = safe_join(HOME_DIRECTORY, path)

    # Ensure the path is within the HOME_DIRECTORY
    if not os.path.commonpath([os.path.abspath(full_path), os.path.abspath(HOME_DIRECTORY)]) == os.path.abspath(HOME_DIRECTORY):
        abort(404)

    if os.path.isdir(full_path):
        # Redirect to index.html within the directory
        index_path = safe_join(full_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(full_path, 'index.html')#redirect(f"/{path}/index.html")
        else:
            abort(404)
    else:
        # If the path is a file, serve it directly
        if os.path.exists(full_path):
            return send_from_directory(HOME_DIRECTORY, path)
        else:
            # If file does not exist, check if it exists in the default image directory
            default_image_path = safe_join(DEFAULT_IMAGE_DIR, os.path.basename(path))
            if os.path.exists(default_image_path):
                return send_from_directory(DEFAULT_IMAGE_DIR, os.path.basename(path))
            else:
                abort(404)
        
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
        gameInfo += "<th><button class=\"btn\">Xbox Live</button></th>"
    if root.find('.//offlineSystemLinkMin', namespaces) is not None:
        gameInfo += "<th><button class=\"btn\">SystemLink</button></th>"
    if root.find('.//onlineCoopPlayersMin', namespaces) is not None:
        gameInfo += "<th><button class=\"btn\">Coop</button></th>"

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

def gamePages(directory):
    try:
        items = os.listdir(directory)
        for item in items:
            if os.path.isdir(os.path.join(directory, item)):
                yield item
    except Exception as e:
        print(f"Error: {e}")

def rebuildIndex(id):
    print(f'Rebuilding index: {id}')
    with open('template.html', 'r', encoding='utf-8') as template_file:
        template = template_file.read()
    
    with open(safe_join(CACHE_DIRECTORY, f"{id.lower()}.xml"), 'r', encoding='utf-8') as xml:
        xml_data = xml.read()
    gallery = ""
    fields = get_fields_from_xml(xml_data)
    pattern = re.compile(r'screenlg\d+\.(jpg|jpeg|png|bmp)$', re.IGNORECASE)
    
    for imgUrl in fields['imageUrls']:
        image_name = imgUrl.split("/")[-1]
        if pattern.search(image_name):
            if image_name not in gallery:
                gallery += f'<div class="gallery-item"><img src="./{image_name}" alt="image"></div>'
    
    content = template.replace('{title}', fields["title"])
    content = content.replace('{id}', id)
    content = content.replace('{description}', fields["description"])
    content = content.replace('{developerName}', fields["developerName"])
    content = content.replace('{releaseDate}', fields["releaseDate"])
    content = content.replace('{publisherName}', fields["publisherName"])
    content = content.replace('{capabilities}', fields["capabilities"])
    content = content.replace('{gallery}', gallery)
    filename = f"{HOME_DIRECTORY}/{id}/index.html"
    with open(filename, mode='w+', encoding='utf-8') as file:
        file.write(content)
