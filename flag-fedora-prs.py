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

pagureurl = 'https://src.fedoraproject.org'

parser = argparse.ArgumentParser()
parser.add_argument("-dry", action="store_true", help="Do not actually modify the flag")
parser.add_argument("-workflow", required=True, help="Path to Workflow")
parser.add_argument("-uid", required=True, help="UID of Pagure flag")
parser.add_argument("-token", default="/etc/pagure_flag_token", help="Config file containing Pagure token")
parser.add_argument("-artifacts", default="https://mbi-artifacts.s3.eu-central-1.amazonaws.com", help="URL to MBICI artifact storage")
parser.add_argument("prs", nargs='*', help="Fedora dist-git pull requests to flag")
args = parser.parse_args()

with open(args.token) as f:
    paguretoken = f.read().rstrip()

wf = ET.parse(args.workflow)
wf_tasks = set(x for x in wf.findall('task'))
wf_results = set(x for x in wf.findall('result'))
wf_failed = set(x for x in wf_results if x.find('outcome').text != 'SUCCESS')

status = 'error'
if wf_failed:
    status = 'failure'
elif len(wf_tasks) == len(wf_results):
    status = 'success'
else:
    status = 'pending'

messages = {
    'success': 'Test passed',
    'failure': 'Test failed',
    'error': 'There was an error running test',
    'pending': 'Test is running',
    'canceled': 'Test was cancelled',
}
if status not in messages:
    raise Exception(f'Bad status: {status}')

headers = {
    'Authorization': f'token {paguretoken}',
    'User-Agent': 'MBICI',
}

data = {
    'username': 'MBI - Maven Bootstrap Initiative',
    'status': status,
    'comment': messages[status],
    'url': f'{args.artifacts}/{args.uid}/result.html',
    'uid': args.uid.replace('-',''),
}

PR_RE = re.compile(f'^(.+)/rpms/([^/]+)/pull-request/([1-9][0-9]*)$')

for pr in args.prs:
    match = PR_RE.match(pr)
    if match:
        repo = match.group(2)
        prid = match.group(3)
        target_url = f'{pagureurl}/api/0/rpms/{repo}/pull-request/{prid}/flag'
        print(target_url)
        print(data)
        if not args.dry:
            req = requests.post(target_url, headers=headers, data=data)
            print(req.status_code)
            print(req.text)
