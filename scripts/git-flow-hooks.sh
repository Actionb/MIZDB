#!/usr/bin/env bash
# Install the hooks for auto-incrementing the VERSION file from the
# git-flow-hooks repository.

TMP_DIR=/tmp/git-flow-hooks
HOOKS_DIR=$(git rev-parse --git-dir)/hooks

git clone https://github.com/jaspernbrouwer/git-flow-hooks $TMP_DIR

set -x
cp -r $TMP_DIR/modules "$HOOKS_DIR"/modules

cp $TMP_DIR/{post-flow-{release,hotfix}-start,filter-flow-{release,hotfix}-start-version,filter-flow-{release,hotfix}-finish-tag-message,LICENSE} "$HOOKS_DIR"

rm -rf $TMP_DIR
set +x
