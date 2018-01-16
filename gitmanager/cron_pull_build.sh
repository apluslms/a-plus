#!/bin/bash

TRY_PYTHON=$1
key=$2
id=$3
url=$4
branch=$5
echo "Processing key=$key id=$id url=$url branch=$branch python=$TRY_PYTHON"

if [ -d exercises ]; then
  CDIR=exercises
else
  CDIR=courses
fi

if [ -f $TRY_PYTHON ]; then
  source $TRY_PYTHON
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
  git submodule update --init --recursive
  git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
else
  git clone -b $branch --recursive $url $dir
  cd $dir
fi

# Build course material.
if [ -e build.sh ]; then
  /bin/bash build.sh
fi
cd ../..

# Link to static.
static_dir=`python gitmanager/cron.py static $key`
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
