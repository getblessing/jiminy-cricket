import os
from pyblish import api

ICON = os.path.join(os.path.dirname(api.__file__), "icons", "logo-32x32.svg")


def show(parent=None):
    """Try showing the most desirable GUI

    This function cycles through the currently registered
    graphical user interfaces, if any, and presents it to
    the user.

    """

    return _discover_gui()(parent)


def _discover_gui():
    """Return the default GUI"""
    try:
        gui = __import__("pyblish_qml").show
    except (ImportError, AttributeError):
        gui = __import__("pyblish_lite").show
    else:
        return gui

    raise ImportError("No Pyblish GUI found")
