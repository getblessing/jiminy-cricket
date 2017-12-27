from maya import cmds
import os


def publish_repo():
    return os.path.join(
        cmds.workspace(q=True, rootDirectory=True),
        "publish"
    )


def publish_template():
    file_name_tamplate = "{asset}.{subset}.{representation}"
    return "{publish}/{silo}/{asset}/{subset}/" + file_name_tamplate
