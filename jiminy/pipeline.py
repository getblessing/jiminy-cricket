import os
import sys
import types
import logging
import inspect
import weakref
import traceback
import importlib

from maya import cmds, OpenMaya
from pyblish import api as pyblish
from .vendor.Qt import QtCore, QtWidgets

from . import (
    lib,

    Session,

    _registered_root,
    _registered_config,
    _registered_plugins,
    _registered_plugin_paths,
    _registered_event_handlers,
)

from .vendor import six


log = logging.getLogger(__name__)

self = sys.modules[__name__]
self._menu = "jiminymaya"  # Unique name of menu
self._events = dict()  # Registered Maya callbacks
self._parent = None  # Main Window

IS_HEADLESS = not hasattr(cmds, "about") or cmds.about(batch=True)


def install():
    log.info("Jiminy Cricket, at your service.")

    _register_callbacks()

    if not IS_HEADLESS:
        _install_menu()

    pyblish.register_host("maya")

    config = find_config()
    config.install()
    register_config(config)


def uninstall():
    log.info("Farewell, my friend.")
    config = registered_config()
    config.uninstall()
    deregister_config()

    if not IS_HEADLESS:
        _uninstall_menu()


def find_config():
    log.info("Finding configuration for project..")

    config = os.environ.get("JIMINY_DRESS")

    if not config:
        raise EnvironmentError("No configuration found.")

    log.info("Found %s, loading.." % config)
    return importlib.import_module(config)


def register_config(config):
    _registered_config["_"] = config


def deregister_config():
    _registered_config["_"] = None


def registered_config():
    """Return currently registered config"""
    return _registered_config["_"]


def _install_menu():
    from .tools import (
        #creator,
        #loader,
        publish,
    )

    _uninstall_menu()

    self._parent = {
        widget.objectName(): widget
        for widget in QtWidgets.QApplication.topLevelWidgets()
    }["MayaWindow"]

    def deferred():
        cmds.menu(self._menu,
                  label="Pipeline",
                  tearOff=True,
                  parent="MayaWindow")
        """
        cmds.menuItem("Create...",
                      command=lambda *args: creator.show(parent=self._parent))

        cmds.menuItem("Load...",
                      command=lambda *args:
                      loader.show(parent=self._parent))
        """
        cmds.menuItem("Publish...",
                      command=lambda *args: publish.show(parent=self._parent),
                      image=publish.ICON)

        cmds.menuItem(divider=True, label="Create...")

    # Allow time for uninstallation to finish.
    QtCore.QTimer.singleShot(100, deferred)


def _uninstall_menu():
    app = QtWidgets.QApplication.instance()
    widgets = dict((w.objectName(), w) for w in app.allWidgets())
    menu = widgets.get(self._menu)

    if menu:
        menu.deleteLater()
        del(menu)


def create(name, asset, family, options=None, data=None):
    """Create a new instance

    Associate nodes with a subset and family. These nodes are later
    validated, according to their `family`, and integrated into the
    shared environment, relative their `subset`.

    Data relative each family, along with default data, are imprinted
    into the resulting objectSet. This data is later used by extractors
    and finally asset browsers to help identify the origin of the asset.

    Arguments:
        name (str): Name of subset
        asset (str): Name of asset
        family (str): Name of family
        options (dict, optional): Additional options from GUI
        data (dict, optional): Additional data from GUI

    Raises:
        NameError on `subset` already exists
        KeyError on invalid dynamic property
        RuntimeError on host error

    Returns:
        Name of instance

    """
    plugins = list()
    for Plugin in discover(Creator):
        has_family = family == Plugin.family

        if not has_family:
            continue

        Plugin.log.info(
            "Creating '%s' with '%s'" % (name, Plugin.__name__)
        )

        try:
            plugin = Plugin(name, asset, options, data)

            with lib.maintained_selection():
                print("Running %s" % plugin)
                instance = plugin.process()
        except Exception as e:
            log.warning(e)
            continue

        plugins.append(plugin)

    assert plugins, "No Creator plug-ins were run, this is a bug"
    return instance


@lib.log
class Loader(list):
    """Load representation into host application

    Arguments:
        context (dict): avalon-core:context-1.0
        name (str, optional): Use pre-defined name
        namespace (str, optional): Use pre-defined namespace

    .. versionadded:: 4.0
       This class was introduced

    """

    families = list()
    representations = list()
    order = 0

    def __init__(self, context):
        template = context["project"]["config"]["template"]["publish"]

        data = {
            key: value["name"]
            for key, value in context.items()
        }

        data["root"] = registered_root()
        data["silo"] = context["asset"]["silo"]

        fname = template.format(**data)
        self.fname = fname

    def load(self, context, name=None, namespace=None, data=None):
        """Load asset via database

        Arguments:
            context (dict): Full parenthood of representation to load
            name (str, optional): Use pre-defined name
            namespace (str, optional): Use pre-defined namespace
            data (dict, optional): Additional settings dictionary

        """
        raise NotImplementedError("Loader.load() must be "
                                  "implemented by subclass")

    def update(self, container, representation):
        """Update `container` to `representation`

        Arguments:
            container (avalon-core:container-1.0): Container to update,
                from `host.ls()`.
            representation (dict): Update the container to this representation.

        """
        raise NotImplementedError("Loader.update() must be "
                                  "implemented by subclass")

    def remove(self, container):
        """Remove a container

        Arguments:
            container (avalon-core:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted

        """

        raise NotImplementedError("Loader.remove() must be "
                                  "implemented by subclass")


@lib.log
class Creator(object):
    """Determine how assets are created"""
    name = None
    label = None
    family = None

    def __init__(self, name, asset, options=None, data=None):
        self.name = name or self.name
        self.options = options

        # Default data
        self.data = dict({
            "id": "pyblish.jiminy.instance",
            "family": self.family,
            "asset": asset,
            "subset": name,
            "active": True
        }, **(data or {}))

    def process(self):
        nodes = list()

        if (self.options or {}).get("useSelection"):
            nodes = cmds.ls(selection=True)

        instance = cmds.sets(nodes, name=self.name)
        lib.imprint(instance, self.data)

        return instance


def discover(superclass):
    """Find and return subclasses of `superclass`"""

    registered = _registered_plugins.get(superclass, list())
    plugins = dict()

    # Include plug-ins from registered paths
    for path in _registered_plugin_paths.get(superclass, list()):
        path = os.path.normpath(path)

        assert os.path.isdir(path), "%s is not a directory" % path

        for fname in os.listdir(path):
            # Ignore files which start with underscore
            if fname.startswith("_"):
                continue

            mod_name, mod_ext = os.path.splitext(fname)
            if not mod_ext == ".py":
                continue

            abspath = os.path.join(path, fname)
            if not os.path.isfile(abspath):
                continue

            module = types.ModuleType(mod_name)
            module.__file__ = abspath

            try:
                with open(abspath) as f:
                    six.exec_(f.read(), module.__dict__)

                # Store reference to original module, to avoid
                # garbage collection from collecting it's global
                # imports, such as `import os`.
                sys.modules[mod_name] = module

            except Exception as err:
                print("Skipped: \"%s\" (%s)", mod_name, err)
                continue

            for plugin in plugin_from_module(superclass, module):
                if plugin.__name__ in plugins:
                    print("Duplicate plug-in found: %s", plugin)
                    continue

                plugins[plugin.__name__] = plugin

    for plugin in registered:
        if plugin.__name__ in plugins:
            print("Warning: Overwriting %s" % plugin.__name__)
        plugins[plugin.__name__] = plugin

    return sorted(plugins.values(), key=lambda Plugin: Plugin.__name__)


def plugin_from_module(superclass, module):
    """Return plug-ins from module

    Arguments:
        superclass (superclass): Superclass of subclasses to look for
        module (types.ModuleType): Imported module from which to
            parse valid Avalon plug-ins.

    Returns:
        List of plug-ins, or empty list if none is found.

    """

    types = list()

    def recursive_bases(klass):
        r = []
        bases = klass.__bases__
        r.extend(bases)
        for base in bases:
            r.extend(recursive_bases(base))
        return r

    for name in dir(module):

        # It could be anything at this point
        obj = getattr(module, name)

        if not inspect.isclass(obj):
            continue

        # These are subclassed from nothing, not even `object`
        if not len(obj.__bases__) > 0:
            continue

        # Use string comparison rather than `issubclass`
        # in order to support reloading of this module.
        bases = recursive_bases(obj)
        if not any(base.__name__ == superclass.__name__ for base in bases):
            continue

        types.append(obj)

    return types


def register_plugin(superclass, obj):
    """Register an individual `obj` of type `superclass`

    Arguments:
        superclass (type): Superclass of plug-in
        obj (object): Subclass of `superclass`

    """

    if superclass not in _registered_plugins:
        _registered_plugins[superclass] = list()

    if obj not in _registered_plugins[superclass]:
        _registered_plugins[superclass].append(obj)


def register_plugin_path(superclass, path):
    """Register a directory of one or more plug-ins

    Arguments:
        superclass (type): Superclass of plug-ins to look for during discovery
        path (str): Absolute path to directory in which to discover plug-ins

    """

    if superclass not in _registered_plugin_paths:
        _registered_plugin_paths[superclass] = list()

    path = os.path.normpath(path)
    if path not in _registered_plugin_paths[superclass]:
        _registered_plugin_paths[superclass].append(path)


def registered_plugin_paths():
    """Return all currently registered plug-in paths"""

    # Prohibit editing in-place
    duplicate = {
        superclass: paths[:]
        for superclass, paths in _registered_plugin_paths.items()
    }

    return duplicate


def deregister_plugin(superclass, plugin):
    """Oppsite of `register_plugin()`"""
    _registered_plugins[superclass].remove(plugin)


def deregister_plugin_path(superclass, path):
    """Oppsite of `register_plugin_path()`"""
    _registered_plugin_paths[superclass].remove(path)


def register_root(path):
    """Register currently active root"""
    log.info("Registering root: %s" % path)
    _registered_root["_"] = path


def registered_root():
    """Return currently registered root"""
    return os.path.normpath(
        _registered_root["_"] or
        Session.get("AVALON_PROJECTS") or ""
    )


def on(event, callback):
    """Call `callback` on `event`

    Register `callback` to be run when `event` occurs.

    Example:
        >>> def on_init():
        ...    print("Init happened")
        ...
        >>> on("init", on_init)
        >>> del on_init

    Arguments:
        event (str): Name of event
        callback (callable): Any callable

    """

    if event not in _registered_event_handlers:
        _registered_event_handlers[event] = weakref.WeakSet()

    events = _registered_event_handlers[event]
    events.add(callback)


def before(event, callback):
    """Convenience to `on()` for before-events"""
    on("before_" + event, callback)


def after(event, callback):
    """Convenience to `on()` for after-events"""
    on("after_" + event, callback)


def emit(event, args=None):
    """Trigger an `event`

    Example:
        >>> def on_init():
        ...    print("Init happened")
        ...
        >>> on("init", on_init)
        >>> emit("init")
        Init happened
        >>> del on_init

    Arguments:
        event (str): Name of event
        args (list, optional): List of arguments passed to callback

    """

    callbacks = _registered_event_handlers.get(event, set())
    args = args or list()

    for callback in callbacks:
        try:
            callback(*args)
        except Exception:
            log.warning(traceback.format_exc())


def _register_callbacks():
    for handler, event in self._events.copy().items():
        if event is None:
            continue

        try:
            OpenMaya.MMessage.removeCallback(event)
            self._events[handler] = None
        except RuntimeError as e:
            log.info(e)

    self._events[_on_scene_save] = OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeSave, _on_scene_save
    )

    self._events[_before_scene_save] = OpenMaya.MSceneMessage.addCheckCallback(
        OpenMaya.MSceneMessage.kBeforeSaveCheck, _before_scene_save
    )

    self._events[_on_scene_new] = OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterNew, _on_scene_new
    )

    self._events[_on_maya_initialized] = OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kMayaInitialized, _on_maya_initialized
    )

    self._events[_on_scene_open] = OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterOpen, _on_scene_open
    )

    log.info("Installed event handler _on_scene_save..")
    log.info("Installed event handler _before_scene_save..")
    log.info("Installed event handler _on_scene_new..")
    log.info("Installed event handler _on_maya_initialized..")
    log.info("Installed event handler _on_scene_open..")


def _on_maya_initialized(*args):
    emit("init", args)

    if cmds.about(batch=True):
        log.warning("Running batch mode ...")
        return

    # Keep reference to the main Window, once a main window exists.
    self._parent = {
        widget.objectName(): widget
        for widget in QtWidgets.QApplication.topLevelWidgets()
    }["MayaWindow"]


def _on_scene_new(*args):
    emit("new", args)


def _on_scene_save(*args):
    emit("save", args)


def _on_scene_open(*args):
    emit("open", args)


def _before_scene_save(return_code, client_data):

    # Default to allowing the action. Registered
    # callbacks can optionally set this to False
    # in order to block the operation.
    OpenMaya.MScriptUtil.setBool(return_code, True)

    emit("before_save", [return_code, client_data])
