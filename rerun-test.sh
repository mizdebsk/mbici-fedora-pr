#!/bin/sh
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

set -eu

plan=/home/kojan/git/mbici-config/plan/bootstrap-maven-rawhide.xml
platform=/home/kojan/git/mbici-config/platform/rawhide-jdk.xml
resultDir=/mnt/nfs/mbi-result/pr
cacheDir=/mnt/nfs/mbi-cache
workDir=/tmp
PATH=$PATH:/home/kojan/git/mbici-workflow/target

uid=$(cat test/uid.txt)
echo === UID: $uid === >&2

echo === Running Workflow... >&2
mbici-wf kube-exec \
     --namespace mbici-pr \
     --max-checkout-tasks 10 \
     --max-srpm-tasks 500 \
     --max-rpm-tasks 200 \
     --workflow test/workflow.xml \
     --result-dir "$resultDir" \
     --cache-dir "$cacheDir" \
     --work-dir "$workDir"

echo === Generating final report... >&2
rm -rf test/report/
mbici-wf report \
     --plan "$plan" \
     --platform "$platform" \
     --subject test/subject.xml \
     --workflow test/workflow.xml \
     --result-dir "$resultDir" \
     --report-dir test/report

echo === Uploading final report to AWS... >&2
s3cmd put -r --acl-public test/report/* s3://mbi-artifacts/$uid/

echo === Flagging PRs... >&2
./flag-fedora-prs.py -uid $uid -workflow test/workflow.xml $@
