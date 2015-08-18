#!/bin/bash
# A sub script for manage_sandbox.sh that creates or updates a
# sandbox installation. See the master script for more info.

# Assign arguments
sbd=$1
target=$2

if [ ! $(type -t echo_err) = 'function' ]; then
  echo 'USE THIS ONLY THROUGH manage_sandbox.sh!'
  exit 1
elif [ $# -ne 2 ]; then
  echo_err 'Invalid number of arguments!'
  exit 1
elif [ "$target" = 'all' ]; then
  echo "About to install all courses:"
  find ./exercises -mindepth 1 -maxdepth 1 -type d
elif [ ! -d ./exercises/$target ]; then
  echo_err 'Invalid target "'$target'"!'
  exit 1
fi

if [ -f $sbd/bin/bash ]; then update=true; else update=false; fi

if $update; then
  ask_yn 'Really update your sandbox at "'$sbd'"?' || exit 1
else
  ask_yn 'Really create new sandbox to "'$sbd'"?' || exit 1
  echo_ok "*** Getting and using debootstrap to create chroot system"
  apt-get -qy install debootstrap
  rm -rf "$sbd"
  debootstrap precise "$sbd" ftp://ftp.funet.fi/pub/Linux/mirrors/ubuntu/archive
  rv=$?
  if [ $rv -ne 0 ]; then
    echo_err "*** ERROR during debootstrap, try again!"
    exit $rv
  fi
  chroot $sbd locale-gen en_US.UTF-8 fi_FI.UTF-8 en_DK.UTF-8
  chroot $sbd update-locale LANG=en_US.UTF-8
fi

# Mount proc to sandbox.
if ! grep --quiet $sbd/proc /etc/fstab
then
  echo_ok "*** Mounting sandbox proc"
  echo "proc $sbd/proc proc defaults 0 0" >> /etc/fstab
  mount proc $sbd/proc -t proc
fi

# Drop test user (666) network access.
IPTABLES=/etc/iptables.rules
if [ ! -f $IPTABLES ] || ! grep --quiet "uid-owner 666" $IPTABLES
then
  echo_ok "*** Creating or updating $IPTABLES"
  iptables -A OUTPUT -p tcp -m owner --uid-owner 666 -m multiport --ports 30000 -j ACCEPT
  iptables -A OUTPUT -m owner --uid-owner 666 -j REJECT
  iptables-save > $IPTABLES
fi
IPTABLES=/etc/network/if-up.d/iptables
if [ ! -f $IPTABLES ]
then
  echo_ok "*** Creating $IPTABLES"
  echo "#!/bin/bash" > $IPTABLES
  echo "iptables-restore < /etc/iptables.rules" >> $IPTABLES
  chmod +x $IPTABLES
fi

# Create tmp directories.
echo_ok "*** Confirming tmp directories"
mkdir -p $sbd/tmp/grader
chmod 711 $sbd/tmp/grader

# Compile program for running scripts inside the chroot sandbox.
echo_ok "*** Compiling chroot script runner program"
gcc -o scripts/chroot_execvp scripts/chroot_execvp.c
chown root:root scripts/chroot_execvp
chmod 4755 scripts/chroot_execvp

# Add general sandbox scripts.
echo_ok "*** Copying general sandbox scripts"
mkdir -p $sbd/usr/local/sandbox
chmod a+rx $sbd/usr/local/sandbox
find $sbd/usr/local/sandbox -maxdepth 1 -type f -exec rm {} +
cp --preserve=mode $REPO_ROOT_DIR/scripts/sandbox/* $sbd/usr/local/sandbox/

# Add exercise sandbox scripts.
echo_ok "*** Copying course-specific sandbox scripts"
for course_dir in $REPO_ROOT_DIR/exercises/*; do
  if [ -d $course_dir/sandbox ]; then
    course=${course_dir##*/}
    if [ ! "$target" = 'all' -a ! "$target" = "$course" ]; then
      continue # Skip untargeted courses
    fi
    echo_ok '*** Copying sandbox scripts for course "'$course'"'
    rm -rf $sbd/usr/local/sandbox/$course
    cp -r --preserve=mode $course_dir/sandbox $sbd/usr/local/sandbox/$course
    chmod a+rx $sbd/usr/local/sandbox/$course

    # Add requested available scripts.
    if [ -f $course_dir/sandbox/from_sandbox_available ]; then
      for name in $(cat $course_dir/sandbox/from_sandbox_available); do
        src=$REPO_ROOT_DIR/scripts/sandbox_available/$name
        if [ -f $src ]; then
          cp $src $sbd/usr/local/sandbox/
        fi
      done
    fi
  fi
done

# Fix the usual mistake of forgetting execute bit.
find $sbd/usr/local/sandbox -name \*.sh -exec chmod a+rx "{}" +

# Run install scripts.
echo_ok "*** Running other sandbox install scripts"
chroot $sbd /usr/local/sandbox/install.sh $target $sbd

# Finished
echo_ok "*** Install process finished"

# EOF
