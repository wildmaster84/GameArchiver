from app import app
from app.utils import gamePages
from app.utils import rebuild_index
import os

if __name__ == '__main__':
    HOME_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Pages'))
    for game in gamePages(HOME_DIRECTORY):
        rebuild_index(game)
    app.run(host='0.0.0.0', port=10038)
