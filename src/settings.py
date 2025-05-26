#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2025 THL A29 Limited
#
# This source code file is made available under Apache License
# See LICENSE for details
# ==============================================================================


import os


VERSION = "1.0.1"


PLATFORMS = {
    "linux2": "linux",
    "linux": "linux",
    "win32": "windows",
    "darwin": "mac",
}


TOOL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools")
PMD_HOME = os.path.join(TOOL_DIR, "pmd-bin-7.13.0")
os.environ["PATH"] = os.pathsep.join(
    [
        os.path.join(PMD_HOME, "bin"),
        os.environ["PATH"],
    ]
)
