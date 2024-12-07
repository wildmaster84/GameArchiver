from app import app
from app.utils import gamePages
from app.utils import rebuild_index
from app.utils import HOME_DIRECTORY
from app.utils import CACHE_DIRECTORY
import os
import json
from concurrent.futures import ThreadPoolExecutor

def rebuild_all_indexes():
    collected_data = {}

    # Use ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(rebuild_index, game, collected_data) for game in gamePages(HOME_DIRECTORY())]
        for future in futures:
            future.result()

    # Write the collected data to a JSON file
    with open(f'{CACHE_DIRECTORY()}/data.json', 'w', encoding='utf-8') as json_file:
        json.dump(collected_data, json_file, indent=4)

if __name__ == '__main__':
    rebuild_all_indexes()
    app.run(host='0.0.0.0', port=10038, threaded=True)