#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (c) 2025 THL A29 Limited
#
# This source code file is made available under Apache License
# See LICENSE for details
# ==============================================================================


import re
import os
import sys
import json
import fnmatch
import argparse
import subprocess
import multiprocessing

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import settings

class Tool(object):
    def __parse_args(self):
        """
        解析命令
        :return:
        """
        argparser = argparse.ArgumentParser()
        subparsers = argparser.add_subparsers(dest="command", help="Commands", required=True)
        # 检查在当前机器环境是否可用
        subparsers.add_parser("check", help="检查在当前机器环境是否可用")
        # 执行代码扫描
        subparsers.add_parser("scan", help="执行代码扫描")
        return argparser.parse_args()

    def __get_task_params(self):
        """
        获取需要任务参数
        :return:
        """
        task_request_file = os.environ.get("TASK_REQUEST")

        with open(task_request_file, "r") as rf:
            task_request = json.load(rf)

        task_params = task_request["task_params"]
        task_params["task_dir"] = os.path.abspath(task_request["task_dir"])

        # ------------------------------------------------------------------ #
        # 获取需要扫描的文件列表
        # 此处获取到的文件列表,已经根据项目配置的过滤路径过滤
        # 增量扫描时，从SCAN_FILES获取到的文件列表与从DIFF_FILES获取到的相同
        # ------------------------------------------------------------------ #
        task_params["scan_files"] = os.getenv("SCAN_FILES")

        return task_params

    def __get_dir_files(self, root_dir, want_suffix=""):
        """
        在指定的目录下,递归获取符合后缀名要求的所有文件
        :param root_dir:
        :param want_suffix:
                    str|tuple,文件后缀名.单个直接传,比如 ".py";多个以元组形式,比如 (".h", ".c", ".cpp")
                    默认为空字符串,会匹配所有文件
        :return: list, 文件路径列表
        """
        files = set()
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                if f.lower().endswith(want_suffix):
                    fullpath = os.path.join(dirpath, f)
                    files.add(fullpath)
        files = list(files)
        return files

    def __format_str(self, text):
        """
        格式化字符串
        :param text:
        :return:
        """
        text = text.strip()
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        return text.strip("'\"")

    def __run_cmd(self, cmd_args):
        """
        执行命令行
        """
        print("[run cmd] %s" % " ".join(cmd_args))
        p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdoutput, erroutput) = p.communicate()
        stdoutput = self.__format_str(stdoutput)
        erroutput = self.__format_str(erroutput)
        if stdoutput:
            print(">> stdout: %s" % stdoutput)
        if erroutput:
            print(">> stderr: %s" % erroutput)
        return stdoutput, erroutput, p.returncode

    def __check_usable(self):
        """
        检查工具在当前机器环境下是否可用
        """
        # 这里只是一个demo，检查python3命令是否可用，请按需修改为实际检查逻辑
        check_cmd_args = ["pmd", "--version"]
        try:
            stdout, stderr, retcode = self.__run_cmd(check_cmd_args)
        except Exception as err:
            print("tool is not usable: %s" % str(err))
            return False
        return True

    def run(self):
        args = self.__parse_args()
        if args.command == "check":
            print(">> check tool usable ...")
            is_usable = self.__check_usable()
            result_path = "check_result.json"
            if os.path.exists(result_path):
                os.remove(result_path)
            with open(result_path, "w") as fp:
                data = {"usable": is_usable}
                json.dump(data, fp)
        elif args.command == "scan":
            print(">> start to scan code ...")
            self.__scan()
        else:
            print("[Error] need command(check, scan) ...")

    def __scan(self):
        """
        分析代码
        """
        # 代码目录直接从环境变量获取
        # source_dir = os.environ.get("SOURCE_DIR", None)
        # print("[debug] source_dir: %s" % source_dir)
        result_dir = os.getenv("RESULT_DIR", os.getcwd())
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)

        # 其他参数从task_request.json文件获取
        task_params = self.__get_task_params()

        issues = self.analyze(task_params)
        # print("[debug] issues: %s" % issues)
        # 输出结果json文件到RESULT_DIR指定的目录下
        result_path = os.path.join(result_dir, "result.json")
        with open(result_path, "w") as fp:
            json.dump(issues, fp, indent=2)

    def generate_ruleset(self, params, rule_name, rule_json):
        work_dir = os.path.join(params["task_dir"], "workdir")

        real_name = rule_name.split("/")[-1]
        custom_xml = os.path.join(work_dir, "custom-"+real_name+".xml")
        root = ET.Element("ruleset")
        root.set("name", "custom-"+real_name)
        root.set("xmlns", "http://pmd.sourceforge.net/ruleset/2.0.0")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xsi:schemaLocation", "http://pmd.sourceforge.net/ruleset/2.0.0 http://pmd.sourceforge.net/ruleset_2_0_0.xsd")

        description = ET.SubElement(root, "description")
        description.text = "Custom rule."

        rule1 = ET.SubElement(root, "rule")
        rule1.set("ref", rule_name)
        properties1 = ET.SubElement(rule1, "properties")
        property1 = ET.SubElement(properties1, "property")
        property1.set("name", rule_json["name"])
        property1.set("value", rule_json["value"])

        tree = ET.ElementTree(root)
        tree.write(custom_xml, encoding="utf-8", xml_declaration=True)

        return custom_xml + "/" + real_name

    def analyze(self, params):
        source_dir = os.environ.get("SOURCE_DIR", None)
        work_dir = os.path.join(params["task_dir"], "workdir")
        rules = params["rules"]
        rule_list = params["rule_list"]
        # filter_mgr = FilterPathUtil(params)
        error_output = os.path.join(work_dir, "PMDErrorOutput.xml")

        # enabled rules
        default_rules = list()
        custom_rules = list()
        # Server传来规则，需要将之分为pmd自带规则和自定义规则
        for rule in rule_list:
            rule_name = rule["name"]
            rule_params = rule["params"]
            if rule_name.startswith("custom_"):
                custom_rules.append(rule_name)
            # 支持规则参数设置
            elif rule_params:
                print(f"规则 {rule_name} 设置了参数 : {rule_params}")
                try:
                    rule_json = json.loads(rule_params)
                    default_rules.append(self.generate_ruleset(params, rule_name, rule_json))
                except Exception as e:
                    print("参数设置错误，采用默认规则：" + e)
                    default_rules.append(rule_name)
            else:
                default_rules.append(rule_name)
        # 添加自定义规则
        used_rules = ",".join(default_rules + self.__get_dir_files(os.path.join(os.path.dirname(settings.TOOL_DIR), "plugins"), ".xml"))
        # print(used_rules)

        # 增量分析 cache
        cache_path = os.path.join(work_dir, "cache")
        open(cache_path, 'a').close()

        # 文件列表路径，绝对路径
        scan_files_env = params["scan_files"]
        scan_files = list()
        if scan_files_env and os.path.exists(scan_files_env):
            with open(scan_files_env, "r") as rf:
                scan_files = json.load(rf)
                # print("[debug] files to scan: %s" % len(scan_files))
        tool_files_path = os.path.join(work_dir, "pmd_filelist.txt")
        with open(tool_files_path, "w") as rf:
            rf.write("\n".join(scan_files))

        scan_cmd = [
            "pmd",
            "check",
            "-R",
            used_rules,
            "--format",
            "xml",
            # 检测到issue返回值也为0
            "--no-fail-on-violation",
            # 执行异常返回值也为0
            # "--no-fail-on-error",
            "-r",
            error_output,
            # "--debug",
            "--encoding",
            "utf-8",
            # "-d",
            # source_dir,
            "--cache",
            cache_path,
            "--threads",
            f"{multiprocessing.cpu_count()}",
            "--file-list",
            tool_files_path,
        ]
        try:
            _, stderr, retcode = self.__run_cmd(scan_cmd)
        except Exception as err:
            raise Exception("scan failed: %s" % str(err))
        if retcode > 0:
            raise Exception(f"Tool returncode: {retcode}")

        issues = []

        if not os.path.exists(error_output) or os.stat(error_output).st_size==0:
            print("result is empty")
            return issues

        tree = ET.parse(error_output)
        root = tree.getroot()
        for file in root.getchildren():
            # tag, attrib
            path = file.attrib.get("name")
            for error in file.getchildren():
                line = int(error.attrib.get("beginline"))
                column = int(error.attrib.get("begincolumn"))
                # rule real name
                ruleUrl = error.attrib.get("externalInfoUrl", None)
                if ruleUrl.startswith("https://"):
                    keyword = "rules_"
                    pos = ruleUrl.find(keyword)
                    rule = ruleUrl[pos+len(keyword):]
                    rule = rule.replace("html#", "xml/")
                    rule = rule.replace("_", "/")
                else:
                    rule = ruleUrl
                print(f"rule: {rule}")
                real_rule_name = None
                for item in rules:
                    if not item.lower().endswith(rule):
                        continue
                    real_rule_name = item
                    break
                if real_rule_name is None:
                    continue
                msg = error.text + ruleUrl
                issues.append({"path": path, "rule": real_rule_name, "msg": msg, "line": line, "column": column})
        # print(issues)

        return issues
