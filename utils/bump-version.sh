#!/bin/bash
VER="$1"

if [[ "x${VER}" = "x" ]]
then
    echo "Usage: $0 <version number>"
    echo " e.g. $0 0.1.0"
    exit 1
fi

function inplace_sed {
    # Note: we don't use sed -i -e ... because it isn't supported by FreeBSD
    # sed on OS X.
    local command="$1"; shift
    local suffix=".inplace.bak"
    sed -i"${suffix}" -e "${command}" "$@"
    for filename in "$@"; do
        rm "${filename}${suffix}"
    done
}

setup_sed="s/\(version[ ]*=[ ]*[\"']\)\(.*\)\([\"'].*\)/\1${VER}\3/"
init_sed="s/^\(__version__[ ]*=[ ]*[\"']\)\(.*\)\([\"'].*\)/\1${VER}\3/"

inplace_sed "${setup_sed}" setup.py verified-fake/setup.py
inplace_sed "${init_sed}" go_contacts/__init__.py

git add setup.py verified-fake/setup.py go_contacts/__init__.py
