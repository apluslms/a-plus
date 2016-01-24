#!/bin/bash -x

FLAG="/tmp/mooc-grader-manager-clean"
if [ -e $FLAG ]; then
  exit 0
fi
touch $FLAG

LOG="/tmp/mooc-grader-log"
QUEUE="/etc/init.d/celeryd"
TOUCH="/etc/uwsgi/grader.ini"
SQL="sqlite3 -batch -noheader db.sqlite3 "
PYTHON="/srv/grader/venv/bin/python"

cd `dirname $0`/..

if [ -x $QUEUE ]; then
  $QUEUE stop
fi

keys=( "`$SQL "select r.key from gitmanager_courseupdate as u left join gitmanager_courserepo r on u.course_repo_id=r.id where u.updated=0;"`" )
for key in $keys; do
  echo "Update $key" > $LOG

  # Update from git origin and move to dir.
  dir=exercises/$key
  id=`$SQL "select id from gitmanager_courserepo where key='$key';"`
  url=`$SQL "select git_origin from gitmanager_courserepo where key='$key';"`
  branch=`$SQL "select git_branch from gitmanager_courserepo where key='$key';"`
  if [ -e $dir ]; then
    cd $dir
    branchnow=`git branch`
    if [ "${branchnow#* }" != "$branch" ]; then
      git checkout $branch >> $LOG
    fi
    git pull >> $LOG
  else
    git clone -b $branch $url $dir >> $LOG
    cd $dir
  fi

  # Build course material.
  if [ -e build.sh ]; then
    /bin/bash build.sh >> $LOG
  fi
  cd ../..

  # Link to static.
  static_dir=`$PYTHON cron.py static $dir`
  if [ "$static_dir" != "" ]; then
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

  # Update sandbox.
  ./manage_sandbox.sh create $key >> $LOG

  # Write to database.
  data=`$PYTHON cron.py log $LOG`
  $SQL "update gitmanager_courseupdate set log='$data',updated_time=CURRENT_TIMESTAMP,updated=1 where key='$key' and updated=0;"

  # Clean up old entries.
  last=`$SQL "select request_time from gitmanager_courseupdate where id=$id order by request_time desc limit 4,1;"`
  if [ "$last" != "" ]; then
    $SQL "delete from gitmanager_courseupdate where id=$id and request_time > '$last';"
  fi
done

touch $TOUCH

if [ -x $QUEUE ]; then
  $QUEUE start
fi
