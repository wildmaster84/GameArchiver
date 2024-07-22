from flask import send_from_directory, render_template, abort, send_file, redirect, request
import os
from werkzeug.utils import safe_join
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re
from app import app
from app.utils import gamePages
from app.utils import HOME_DIRECTORY
from app.utils import CACHE_DIRECTORY
from app.utils import DEFAULT_IMAGE_DIR
from app.utils import CRUMBS
import json

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
def is_image(path):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    return any(path.lower().endswith(ext) for ext in image_extensions)

@app.before_request
def before_request_func():
    block_malformed_requests()
    if request.path.endswith("index.html"):
        new_path = request.path[:-11]  # Remove "index.html" from the path
        return redirect(new_path)
    if request.path.endswith("//"):
        new_path = request.path[:-1]  # Remove "index.html" from the path
        return redirect(new_path)

@app.errorhandler(404)
def page_not_found(e):
    path = request.path.strip()
    parent_dir = os.path.dirname(path)
    if path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        # Extract the image name
        image_name = os.path.basename(path)
        print(f"Missing image: {path}")
        return send_from_directory(DEFAULT_IMAGE_DIR(), image_name)
    else:
        message = '{"status":"404", "error": "Requested resource could not be found"}'
        return message, 404

@app.errorhandler(500)
def internal_server_error(e):
    message = '{"status":"500", "error": "Internal server error"}'
    return message, 500

@app.route('/search')
def search():
    game_data = CRUMBS()
    query = request.args.get('q', '').lower()
    page = request.args.get('page', 1, type=int)
    chunk_size = 14
    results = [(id, data) for id, data in game_data.items() if query in data['title'].lower() or query in id.lower()]
    paged_results = list(chunk_array(results, chunk_size))
    total_pages = len(paged_results)
    
    if page < 1 or page > total_pages:
        page = 1 
    
    current_page_results = paged_results[page-1] if paged_results else []
    
    return render_template(
        'search.html', 
        directories=current_page_results, 
        total=len(results), 
        page=page, 
        total_pages=total_pages, 
        hostname=request.host,
        query=query,
        max=max, 
        min=min
    )

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    chunk_size = 84
    collected_data = CRUMBS()
    directories = list(collected_data.keys())
    paged_directories = list(chunk_array(directories, chunk_size))
    total_pages = len(paged_directories)

    if page < 1 or page > total_pages:
        page = 1  # Default to the first page if the page number is invalid

    # Get the full paths
    directories_with_data = [(name, collected_data[name]) for name in paged_directories[page-1]]
    return render_template(
        'home.html', 
        total=len(directories), 
        directories=directories_with_data, 
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
    safe_file_id = safe_join(CACHE_DIRECTORY(), f"{path.strip().lower()}.xml")
    if os.path.exists(safe_file_id):
        return send_file(safe_file_id, as_attachment=False, mimetype='application/xml')
    else:
        abort(404)

@app.route('/api/json/<path:path>')
def api_json(path):
    
    for id, data in CRUMBS().items():
        if len(path.strip().lower()) == 8:
            if path.strip().lower() in id.lower():
                return CRUMBS()[id]
        else:
            return CRUMBS()["00000000"]

@app.route('/<path:path>')
def serve_file_or_directory(path):
    directory_id = path.strip().upper().split('/')[0]
    image_name = os.path.basename(path)
    full_path = safe_join(HOME_DIRECTORY(), f"{directory_id}/{image_name}")
    if is_image(full_path):
        if os.path.exists(full_path):
            return send_from_directory(HOME_DIRECTORY(), f"{directory_id}/{image_name}")
        else:
            abort(404)
    
    collected_data = CRUMBS()
    if directory_id in collected_data:
        data = collected_data[directory_id]
        return render_template(
            'game.html',
            id=directory_id,
            title=data["title"],
            description=data["description"],
            developerName=data["developerName"],
            releaseDate=data["releaseDate"],
            publisherName=data["publisherName"],
            capabilities=data["capabilities"],
            gallery=data["gallery"],
            banner=data["banner"]
        )
    else:
        if len(directory_id) == 8:
            data = collected_data["00000000"]
            return render_template(
                'game.html',
                id="00000000",
                title=data["title"],
                description=data["description"],
                developerName=data["developerName"],
                releaseDate=data["releaseDate"],
                publisherName=data["publisherName"],
                capabilities=data["capabilities"],
                gallery=data["gallery"]
            )
        else:
            abort(404)
