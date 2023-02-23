#!/usr/bin/python3
#-
# Copyright (c) 2021 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Mikolaj Izdebski

import re
import requests
import xml.etree.ElementTree as ET
import argparse
from subprocess import Popen, PIPE

def resolve_ref(scm, ref):
    p = Popen(["git", "ls-remote", "--exit-code", "--refs", "--heads", scm, ref], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate(b"")
    if p.returncode != 0:
        raise Exception(f'git ls-remote failed with exit code {p.returncode}; stderr: {err}')
    return output.decode().split()[0]

parser = argparse.ArgumentParser()
parser.add_argument("-plan", required=True, help="Path to Build Plan")
parser.add_argument("-scm", default="https://src.fedoraproject.org/rpms", help="SCM base URL")
parser.add_argument("-ref", default="rawhide", help="Default SCM commit or ref")
parser.add_argument("-lookaside", default="https://src.fedoraproject.org/lookaside/pkgs/rpms", help="Lookaside cache base URL")
parser.add_argument("prs", nargs='*', help="Fedora dist-git pull requests to override primary SCM")
args = parser.parse_args()

components = set(element.text for element in ET.parse(args.plan).findall('.//component'))

PR_RE = re.compile(f'^(.+)/rpms/([^/]+)/pull-request/([1-9][0-9]*)$')

for pr_url in args.prs:
    match = PR_RE.match(pr_url)
    if not match:
        raise Exception(f'Invalid PR URL: {pr_url}')
    component = match.group(2)
    if component not in components:
        raise Exception(f'Component {component} is not part of test plan')

scms = {}
commits = {}    

for component in components:
    scms[component] = f'{args.scm}/{component}.git'
    commits[component] = resolve_ref(scms[component], args.ref)

for pr_url in args.prs:
    match = PR_RE.match(pr_url)
    pagure_base = match.group(1)
    component = match.group(2)
    pr = match.group(3)
    info = requests.get(f'{pagure_base}/api/0/rpms/{component}/pull-request/{pr}').json()
    web_url = info['full_url']
    if web_url != pr_url:
        raise Exception(f'{web_url} != {pr_url}')
    fork_name = info['repo_from']['fullname']
    scm_name = info['project']['fullname']
    commit = info['commit_stop']
    commits[component] = commit
    scms[component] = f'{pagure_base}/{fork_name}.git'

print(f'<subject>')
for component in sorted(scms.keys()):
    print(f'  <component>')
    print(f'    <name>{component}</name>')
    print(f'    <scm>{scms[component]}</scm>')
    print(f'    <commit>{commits[component]}</commit>')
    print(f'    <lookaside>{args.lookaside}/{component}</lookaside>')
    print(f'  </component>')
print(f'</subject>')
