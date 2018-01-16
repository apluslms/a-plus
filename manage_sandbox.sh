#!/bin/bash
PATH="/bin:/usr/bin:/sbin:/usr/sbin"
cd `dirname $0`

# Functions for internal and sub script use
function echo_err { echo -e "\e[0;31m$1\e[0m"; }
function echo_ok { echo -e "\e[0;32m$1\e[0m"; }
function ask_yn {
  local ans
  while true; do printf "$@ [y/n] "; read ans
    case "$ans" in y|Y) return 0 ;; n|N) return 1 ;; *) continue ;; esac
  done
}
export -f echo_err echo_ok ask_yn
function print_help {
  echo "Manages the grader sandbox installation.

Sandbox is a chroot system installation where user submissions can be
compiled and run without compromising the main system.

The sandbox directory location can be defined with an option flag or
with the environment variable GRADER_SANDBOX_DIR. If unset, the value
/var/sandbox is assumed by default.

Usage $0 [OPTIONS] TASK [ARGS]

Options:
  -h            Print this help.
  -d DIR        Specify a custom sandbox dir over \"$sbd\".
  -q            Quiet mode for example cron jobs.

Tasks:
  create TARG   Create/update the sandbox. The TARG variable must match
                a course directory or the wildcard 'all'.
  shell         Start a sandbox shell as the sandbox user.
  shell-net     As the previous but as a network enabled sandbox user.
  reset         Remove all course specific files from the sandbox.
  delete        Remove the entire sandbox.
  fsc-start     Start the fast scala compilation service for the sandbox user.
  fsc-restart   Restart the fast scala compilation service.
  fsc-stop      Stop the fast scala compilation service.
  mount-dev-shm Create dev/shm for Python multiprocessing.Pool()

The script requires super user priviliges. Enjoy!"
}

# Set defaults
sbd=${GRADER_SANDBOX_DIR:-/var/sandbox}
quiet=0

# Parse options
while getopts "hd:q" opt; do
  case "$opt" in
    'h') print_help; exit 0 ;;
    'd') sbd="${OPTARG%/}"; echo_ok 'Target sandbox: "'$sbd'"' ;;
    'q') quiet=1 ;;
    '?') print_help; echo_err "No such option: $OPTARG!"; exit 1 ;;
    ':') print_help; echo_err "No argument given for option: $OPTARG!"; exit 1 ;;
  esac
done
shift $((OPTIND-1))

# Parse task
task=$1; shift
[ -z "$task" ] && print_help && echo_err 'No task specified!' && exit 1

# Ensure that we have the necessary privileges
if [ $EUID -ne 0 ]; then
  print_help; echo_err "Must be run as root!"; exit 1
fi

# Export variables for sub scripts
export REPO_ROOT_DIR=$(pwd)

case "$task" in
  'create') ./scripts/manage_sandbox__create.sh "$sbd" "$@" "$quiet"; rv=$? ;;
  'shell') chroot $sbd su sandbox; rv=$? ;;
  'shell-net') chroot $sbd su sandboxnet; rv=$? ;;
  'reset')
    ask_yn 'Really reset sandbox at "'$sbd'"?' || exit 1
    find $sbd/usr/local/sandbox -mindepth 1 -maxdepth 1 -type d -exec rm -rf "{}" +
    rv=0
    ;;
  'delete')
    ask_yn 'Really delete the entire sandbox at "'$sbd'"?' || exit 1
    echo_ok "*** Unmounting sandbox proc"; umount "$sbd/proc"
    sed -i "/$(echo "$sbd" | sed -e 's/[\/&]/\\&/g')/d" /etc/fstab
    echo_ok "*** Deleting sandbox"; rm -rf "$sbd"
    echo_err "*** NOT undoing iptables. UID 666 continues to have restricted network"
    rv=0
    ;;
  'fsc-start')
	if [ $quiet -eq 0 ]; then
		./scripts/chroot_execvp - - - - - - fsc.sh --check; rv=$?
	else
		./scripts/chroot_execvp - - - - - - fsc.sh --quietcheck; rv=$?
	fi
	;;
  'fsc-restart') ./scripts/chroot_execvp - - - - - - /usr/local/sandbox/fsc.sh; rv=$? ;;
  'fsc-stop') ./scripts/chroot_execvp - - - - - - /usr/local/sandbox/fsc.sh --shutdown; rv=$? ;;
  'mount-dev-shm')
    echo_ok "*** Mounting /var/sandbox/dev/shm"
    ./scripts/mount_dev_shm.sh
  ;;
  *) print_help; echo_err "Invalid task: $task!"; exit 1 ;;
esac

if [ $rv -eq 0 ]; then
  if [ $quiet -eq 0 ]; then
    echo_ok 'Task "'$task'" finished successfully!'
  fi
else
  echo_err 'Task "'$task'" failed!'
fi

exit $rv

# EOF
