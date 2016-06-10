#!/bin/bash

PYTHON=$1
key=$2
id=$3
url=$4
branch=$5
echo "Processing key=$key id=$id url=$url branch=$branch python=$PYTHON"

if [ -d exercises ]; then
  CDIR=exercises
else
  CDIR=courses
fi

# Update from git origin and move to dir.
dir=$CDIR/$key
if [ -e $dir ]; then
  cd $dir
  branchnow=`git branch`
  if [ "${branchnow#* }" != "$branch" ]; then
    git checkout $branch
  fi
  git pull
else
  git clone -b $branch $url $dir
  cd $dir
fi

# Build course material.
if [ -e build.sh ]; then
  /bin/bash build.sh
fi
cd ../..

# Link to static.
static_dir=`$PYTHON gitmanager/cron.py static $key`
if [ "$static_dir" != "" ]; then
  echo "Link static dir $static_dir"
  cd static
  target="../$dir/$static_dir"
  if [ -e $key ]; then
    if [ "`readlink $key`" != "$target" ]; then
      rm $key
      ln -s $target $key
    fi
  else
    ln -s $target $key
  fi
  cd ..
fi
