#!/bin/bash
#
# Fallback insecure grading when the Linux chroot sandbox is missing.
# This will allow testing graders in most development environments.
# The feedback will always include a warning to prevent production use.
#

if [ $# -lt 7 ]; then
  echo "Sandbox environment is not created. Testing without file or network access restrictions. The process limits may or may not apply depending on your system. NOT READY FOR PRODUCTION!" >&2
  echo "" >&2
fi

if [ "$1" == "net" ]; then
    shift
fi
if [ $# -lt 6 ]; then
    echo "Pretends to run a command in a sandbox environment."
    echo "Usage: $0 [net] time heap files disk dir prg [args...]"
    echo "    1k for kilobyte, m for mega, g for giga and - for unlimited"
    echo "    net          enables network (optional and ignored)"
    echo "    time         maximum time for process in seconds"
    echo "    memory       maximum memory size"
    echo "    files        maximum number of open file descriptors"
    echo "    disk         maximum disk write size"
    echo "    dir          a target directory or -"
    echo "    course_key   a course key for building PATH"
    echo "    prg          a program to envoke"
    echo "    args         any arguments for program (optional)"
    exit 0
fi

cd `dirname $0`/..
ROOT=`pwd`
CMD=

# Working dir.
if [ $5 != "-" ]; then
    cd $5
else
    cd /tmp
fi

export PATH=".:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:$ROOT/scripts/sandbox:$ROOT/exercises/$6/sandbox"

# Limit process.
function parse_size
{
    if [[ $1 == *[kK] ]]; then
        size=${1%k}
    elif [[ $1 == *[mM] ]]; then
        size=${1%m}
        let size*=1024
    elif [[ $1 == *[gG] ]]; then
        size=${1%g}
        let size*=1048576
    else
        size=$1
        let size/=1024
    fi
}
if [ $1 != "-" ] && type timeout >/dev/null 2>&1; then
    CMD="timeout $1s "
fi
if type ulimit >/dev/null 2>&1; then
    if [ $2 != "-" ]; then
        parse_size $2
        ulimit -v $size
    fi
    if [ $3 != "-" ]; then
        ulimit -n $3
    fi
    if [ $4 != "-" ]; then
        parse_size $4
        ulimit -f $size
    fi
fi
shift; shift; shift; shift; shift; shift

if [ $1 == "without_sandbox" ]; then
  shift
fi

# Run command.
CMD="$CMD$@"
$CMD
exit $?
