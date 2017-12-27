"""
Jiminy pipeline entry script

"""
import os
import sys
import ConfigParser


def parse_settings():
    SETTINGS_FILE = ""
    for repo in os.environ["MAYA_PLUG_IN_PATH"].split(os.pathsep):
        _path = os.path.join(repo, "jiminy-settings.txt")
        if os.path.isfile(_path):
            SETTINGS_FILE = _path
    # Read settings
    settings = ConfigParser.ConfigParser()
    settings.optionxform = str
    settings.read(SETTINGS_FILE)

    JIMINY_CORE_PATH = settings.get("JIMINY_CORE", "path")
    JIMINY_DRESS_PATH = settings.get("JIMINY_DRESS", "path")
    JIMINY_DRESS_NAME = settings.get("JIMINY_DRESS", "name")
    PYBLISH_BASE_PATH = settings.get("PYBLISH_BASE", "path")
    PYBLISH_LITE_PATH = settings.get("PYBLISH_LITE", "path")
    PYBLISH_QML_PATH = settings.get("PYBLISH_QML", "path")
    PYBLISH_QML_PYTHON = settings.get("PYBLISH_QML", "python")
    PYBLISH_QML_PYQT5 = settings.get("PYBLISH_QML", "pyqt5")

    # setup !

    sys.path.insert(0, PYBLISH_BASE_PATH)

    if os.path.isfile(PYBLISH_QML_PYTHON) and os.path.isdir(PYBLISH_QML_PATH):
        # Assume QML is ready
        sys.path.insert(0, PYBLISH_QML_PATH)
        os.environ["PYBLISH_QML_PYTHON_EXECUTABLE"] = PYBLISH_QML_PYTHON
        os.environ["PYBLISH_QML_PYQT5"] = PYBLISH_QML_PYQT5
        os.environ["PYTHONPATH"] = ";".join(
            [
                PYBLISH_BASE_PATH,
                PYBLISH_QML_PATH,
                PYBLISH_QML_PYQT5,
                os.environ["PYTHONPATH"]
            ]
        )
    else:
        sys.path.insert(0, PYBLISH_LITE_PATH)

    sys.path.insert(0, JIMINY_CORE_PATH)
    sys.path.insert(0, JIMINY_DRESS_PATH)
    os.environ["JIMINY_DRESS"] = JIMINY_DRESS_NAME


def initializePlugin(mobject):
    parse_settings()
    # call core install
    import jiminy.api
    jiminy.api.install()


def uninitializePlugin(mobject):
    # call core uninstall
    import jiminy.api
    jiminy.api.uninstall()
