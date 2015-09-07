# filterstage-gui
Python GUI application to test designs with TMC223 stepper drivers

## Introduction

filterstage-gui is a Python GUI application to control an optical bandpass that is running the [filterstage](https://github.com/myorbit/filterstage/) firmware on an Arduino.

With filterstage-gui it is possible to test this self-designed filterstage. Although it can be used to debug any design based on TMC223 stepper drivers from Trinamic. Many parameters can be set and saved to a configuration file, too.

Note: This also was a first attempt to learn and play with JSON, PySide and threading.

## Requirements

Tested under Linux (Ubuntu 12.04)

```
Python       (2.7.3 tested)
pyserial     (2.6 tested)
PySide       (1.0.6 tested; do not use 1.1.1 - known bad, causing segfaults)
simplejson   (2.3.2 tested)
```

## Usage

To run, use `python filterstage-gui.py`

To generate from Designer UI file:

1. Create GUI with Qt Designer
2. To make UI file readable to Python generate Python code from Designer UI file with `pyside-uic -o filterstage_ui.py filterstage.ui` (or use Makefile)
3. Run...

## Files

* `filterstage-gui.py`   Python program loading UI file with MainWindow
* `filterstage.ui`       Qt Designer UI file
* `filterstage-conf`     Configuration file with stored, JSON formated parameters
* `filterstage_ui.py`    Generated, Python readable UI file
