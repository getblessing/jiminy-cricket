Jiminy
 Publish
    Pyblish
 	Model
 	Rig
 	Surface
 	Anmation
 Project
    x init project
        x add publish folder and json database
    x task manager
        x switch session {silo}{} should not need this anymore
 	asset manager
 		register types
 		register assets
 		register shots
 		register set_dress
 		register char
 	shot builder
 		auto reference


 Model
 	freez, id
 Rig
 	freez, id
 Surface
 	shd


use Master
use .json
use task envVar

{publish-repo}/{silo}/{name}/{subset}

{publish-repo}/asset/{name}/{subset}
{publish-repo}/shots/{name}/{subset}
{publish-repo}/.json


---

pyblish-base
pyblish-qml
    use python3 (python2 need to build pyqt5 yourself)
    pip install pyqt5

```python
import os
import sys

jiminy_root = "C:/Users/David/Dropbox/github/Jiminy-Environ"

Python3 = os.path.join(jiminy_root, "Python3", "python.exe")
pyblish_base = os.path.join(jiminy_root, "pyblish-base")
pyblish_qml = os.path.join(jiminy_root, "pyblish-qml")

sys.path.insert(0, pyblish_base)
sys.path.insert(0, pyblish_qml)

os.environ["PYBLISH_QML_PYTHON_EXECUTABLE"] = Python3
os.environ['PYTHONPATH'] = ";".join(
    [pyblish_base, pyblish_qml, os.environ['PYTHONPATH']]
)
```

pyblish-base
pyblish-lite
```python
import os
import sys

jiminy_root = "C:/Users/David/Dropbox/github/Jiminy-Environ"
sys.path.insert(0, os.path.join(jiminy_root, "pyblish-base"))
sys.path.insert(0, os.path.join(jiminy_root, "pyblish-lite"))

```

Maya
```python
import pyblish
pyblish.api.register_plugin_path(pluginPath)
pyblish.api.register_host("maya") # need ?


import pyblish_qml
pyblish_qml.show()

import pyblish_lite
pyblish_lite.show()

```

### setup/launch ?


### Config

repo name split by '-' and take last word as config name
`something-configname`

### TinyDB

need to test multiple i/o


No loader - by hand

file path template

Animation
    x load char reference
    x load env reference
    x load camera
    o input Cut number
    publish reference list
        publish camera
        publish char cache
        publish aniCurve
