#!/bin/bash
#
# A script that creates a new, isolated state in a git repo that
# has sufficient history to be interesting for purposes of
# testing.

# git makes assumptions about things that look like checksums, so
# never call randname without prefixing its result with some useful
# tag.
function randname
{
    {
	if [ ! -f /dev/urandom ]; then
	    sh -c 'date ; echo $$'
	else
	    head --bytes 1024 /dev/urandom
	fi
    } | md5sum | head --bytes 10
}

git status >/dev/null || exit 1

function create_branch
{
    git checkout -b "${1}"
    echo "$1"
}

function create_mainline
{
    local mainline=$(randname)
    echo "$(create_branch "main_$mainline")"
}

function create_branch_n
{
    local branch="${1-branch0}_$(randname)"
    echo "$(create_branch "$branch")"
}

function create_change
{
    local msg="$1"
    local file="$2"
    local branch="$3"

    (git checkout "$branch" && (echo "file data $(randname)" > "$file" ) && \
	git add "$file" && git commit -m "$msg" "$file") || \
	exit 1
}

function rebase_and_merge
{
    local branch="$1"
    local mainline="$2"

    git checkout "$branch" && git rebase "$mainline" && \
	git checkout "$mainline" && git merge "$branch"
}

function plain_merge
{
    local branch="$1"
    local mainline="$2"

    git checkout "$mainline" && git merge -s ours "$branch"
}

function edits_on
{
    local edit_count="$1"; shift
    local msg="$1"; shift
    local file="$1"; shift

    for the_branch in "$@"; do
	for c in $(seq 1 $edit_count); do
	    create_change "${msg}: $c (branch=$the_branch)" \
		"$file" "$the_branch"
	done
    done
}

testfile="file_$(randname)"
main="$(create_mainline)"
branch_1=$(create_branch_n branch1)

# Something like a normal, FF topic branch merge
edits_on 2 "initial branch edits" "$testfile" "$branch_1"

rebase_and_merge "$branch_1" "$main"

git branch -d "$branch_1"

###################
# Same rebase, but with a conflict.
edits_on 2 "subsequent mainline edits" "$testfile" "$main"

branch_2=$(create_branch_n branch2)

edits_on 2 "rebase edit" "$testfile" "$branch_2" "$main"

rebase_and_merge "$branch_2" "$main"
git checkout --theirs "$testfile" && git add "$testfile" && \
    git rebase --continue -m "resolve merge conflict 1" && \
    git checkout "$main" && git merge "$branch_2"

###################
# Now with timing of conflict in the other direction
edits_on 2 "rebase edit, reversed" "$testfile" "$main" "$branch_2"

rebase_and_merge "$branch_2" "$main"
git checkout --theirs "$testfile" && git add "$testfile" && \
    git rebase --continue -m "resolve merge conflict 1" && \
    git checkout "$main" && git merge "$branch_2"

edits_on 2 "non-ff merge test edit" "$testfile" "$main" "$branch_2"

plain_merge "$branch_2" "$main"

git checkout "$main"
git log --oneline --graph --decorate --all
