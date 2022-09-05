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

rm -rf test/
mkdir test

uid=$(uuidgen)
echo === UID: $uid === >&2
echo $uid >test/uid.txt

echo === Generating Test Subject from PRs... >&2
./subject-from-fedora-prs.py -plan "$plan" $@ >test/subject.xml

echo === Generating Workflow... >&2
mbici-wf generate -plan "$plan" \
     -platform "$platform" \
     -subject test/subject.xml \
     -workflow test/workflow.xml \
     -validate

echo === Generating initial report... >&2
mbici-wf report \
     -plan "$plan" \
     -platform "$platform" \
     -subject test/subject.xml \
     -workflow test/workflow.xml \
     -resultDir "$resultDir" \
     -reportDir test/report

echo === Uploading initial report to AWS... >&2
s3cmd put -r --acl-public test/report/* s3://mbi-artifacts/$uid/

echo === Flagging PRs... >&2
./flag-fedora-prs.py -uid $uid -workflow test/workflow.xml $@

echo === Running Workflow... >&2
mbici-wf run \
     -kubernetesNamespace mbici-pr \
     -maxCheckoutTasks 10 \
     -maxSrpmTasks 500 \
     -maxRpmTasks 200 \
     -maxValidateTasks 20 \
     -workflow test/workflow.xml \
     -resultDir "$resultDir" \
     -cacheDir "$cacheDir" \
     -workDir "$workDir"

echo === Generating final report... >&2
rm -rf test/report/
mbici-wf report \
     -plan "$plan" \
     -platform "$platform" \
     -subject test/subject.xml \
     -workflow test/workflow.xml \
     -resultDir "$resultDir" \
     -reportDir test/report

echo === Uploading final report to AWS... >&2
s3cmd put -r --acl-public test/report/* s3://mbi-artifacts/$uid/

echo === Flagging PRs... >&2
./flag-fedora-prs.py -uid $uid -workflow test/workflow.xml $@
