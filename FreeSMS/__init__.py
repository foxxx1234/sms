import os
import json
from flask import Flask

from . import event_logger

BASE = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "../templates"),
    static_folder=os.path.join(BASE, "../static")
)

app.config.from_file(os.path.join(BASE, "../config.json"), load=json.load)
with open(os.path.join(BASE, "../translations.json"), encoding="utf-8") as fh:
    app.config['TRANSLATIONS'] = json.load(fh)

event_logger.init_db()

import FreeSMS.views
