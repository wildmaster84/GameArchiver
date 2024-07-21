from app import app
from app.utils import gamePages
from app.utils import rebuild_index
import os
from concurrent.futures import ThreadPoolExecutor

def rebuild_all_indexes():
    HOME_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Pages'))
    game_dirs = list(gamePages(HOME_DIRECTORY))

    with ThreadPoolExecutor() as executor:
        executor.map(rebuild_index, game_dirs)

if __name__ == '__main__':
    rebuild_all_indexes()
    app.run(host='0.0.0.0', port=10038, threaded=True)