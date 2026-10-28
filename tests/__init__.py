import os

from src import i18n

i18n.set_language(os.environ.get("TEST_LANG", "en"))
