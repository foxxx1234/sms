import os, json
from flask import Flask

BASE = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "../templates"),
    static_folder=os.path.join(BASE, "../static")
)

app.config.from_file(os.path.join(BASE, "../config.json"), load=json.load)
app.config['TRANSLATIONS'] = json.load(
    open(os.path.join(BASE, "../translations.json"), encoding="utf-8")
)

import FreeSMS.views
