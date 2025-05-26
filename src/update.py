#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2025 THL A29 Limited
#
# This source code file is made available under Apache License
# See LICENSE for details
# ==============================================================================

"""
自动加载pmd规则，汇总成一个json。
"""

import sys, getopt
import os
import re
import json
import codecs

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import settings

want_suffix = [".xml"]

#  python src/update.py -i tools/pmd-pmd_releases-7.13.0
def main(argv):
    """
    下载并指定 PMD 对应版本源代码目录位置。然后执行本脚本，脚本会自动搜多对应的 ruleset.xml 文件，并获取对应的规则信息。
    """
    root_dir = None
    try:
        opts, args = getopt.getopt(argv, "hi:", ["input="])
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-i", "--input"):
            root_dir = arg
    rule_set_paths = _get_all_ruleSets(root_dir)
    rules = _get_all_rules(root_dir, rule_set_paths)

    f = open(os.path.join(os.path.dirname(settings.TOOL_DIR), "config", "pmd.json"))
    config = json.load(f)
    f.close()
    config[0]["checkrule_set"] = rules
    f = open(os.path.join(os.path.dirname(settings.TOOL_DIR), "config", "pmd_new.json"), "w")
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.close()


def _get_all_ruleSets(root_dir):
    rule_set_paths = []
    for lists in os.listdir(root_dir):
        path = os.path.join(root_dir, lists)
        # print path
        if os.path.isdir(path):
            rule_set_paths.extend(_get_all_ruleSets(path))
        else:
            file_extension = tuple(want_suffix)
            if path.endswith(file_extension) and "main/resources/category" in path:
                rule_set_paths.append(path)
    return rule_set_paths


# INFO MINOR -> info
# MAJOR -> warning
# CRITICAL BLOCKER -> error
SEVERITY_MAP = {
    5: "info",
    4: "info",
    3: "warning",
    2: "warning",
    1: "warning",
}

# CODE_SMELL
# BUG
# VULNERABILITY
# SECURITY_HOTSPOT
TYPE_MAP = {
    "codestyle": "convention",
    "design": "convention",
    "documentation": "convention",
    "errorprone": "correctness",
    "bestpractices": "correctness",
    "multithreading": "correctness",
    "performance": "performance",
    "security": "security",
}

LANGUAGE_MAP = {
    # language列表为空，表示通用语言
    "xml": "xml",
    "pom": "xml",
    "wsdl": "xml",
    "xsl": "xml",
    "html": "html",
    "java": "java",
    "jsp": "java",
    "modelica": None,
    "kotlin": "kotlin",
    "ecmascript": "js",
    "scala": "scala",
    "apex": "apex",
    "swift": "swift",
    "visualforce": None, #"visualforce",
    "velocity": None,
    "plsql": "plsql",
}


# 相对路径  规则json
def _get_all_rules(root_dir, rule_sets):
    if not rule_sets:
        return []
    rules = []

    # 前面会根据xmlns添加补充字符串
    for rule_set in rule_sets:
        # print(f"rule_set: {rule_set}")
        tree = ET.parse(rule_set)
        root = tree.getroot()
        prefix = "{" + re.split(r"[{}]", root.tag)[1] + "}"
        urlPostfix = rule_set[: rule_set.find("/")]

        rule_set = rule_set[rule_set.find("category"):]
        # print(f"rule_set: {rule_set}")
        category = rule_set.split("/")[-1][:-4]
        for ruleXml in root.iter(tag=prefix + "rule"):
            # print(ruleXml.tag)
            # print(ruleXml.attrib)
            name = ruleXml.attrib.get("name")
            priority_tag = ruleXml.find(prefix + "priority")
            if priority_tag is not None:
                priority = int(priority_tag.text)
            else:
                priority = 3
            # 过滤废弃的规则
            # ${pmd.website.baseurl}
            url = ruleXml.attrib.get("externalInfoUrl")
            # print(f"url: {url}")
            if not url:
                continue

            # print(f"lang: {ruleXml.attrib.get('language')}")
            rule = {
                "display_name": name,
                "real_name": rule_set + "/" + name,
                "category": TYPE_MAP[category],
                "severity": SEVERITY_MAP[priority],
                "rule_title": ruleXml.attrib.get("message"),
                "custom": False,
                "rule_param": None,
                "languages": [LANGUAGE_MAP[ruleXml.attrib.get("language")]] if LANGUAGE_MAP[ruleXml.attrib.get("language")] is not None else [],
                "solution": None,
                "owner": None,
                "labels": [],
                "disable": False,
            }

            example = ruleXml.find(prefix + "example")
            if example is not None:
                exampleText = example.text
            else:
                exampleText = ""
            description = ruleXml.find(prefix + "description")
            if description is not None:
                descriptionText = description.text
                descriptionText = " ".join(descriptionText.split())
                descriptionText = descriptionText.replace("\n", " ")
            else:
                descriptionText = ""
            # print(f"url: {url}")
            url = url.replace("${pmd.website.baseurl}", f"https://docs.pmd-code.org/pmd-doc-7.13.0")
            rule["description"] = f"{descriptionText}\n{url}\n```\n{exampleText}```"
            rules.append(rule)
    return rules


if __name__ == "__main__":
    main(sys.argv[1:])
