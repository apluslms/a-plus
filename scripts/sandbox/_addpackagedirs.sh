#!/bin/bash
#
# Moves scala/java files to package directories.
# 2007-07-11 Visa Putkinen
# 2013-08-12 Teemu Sirkia

for f in $@
do
  if ! grep -q package $f; then
    continue
  fi

  # package
  PACKAGE=`grep package $f | head -n 1 |
    perl -e 'my $l = <>; $l =~ m/package\s*([a-zA-Z0-9.]*)/; print $1;'`

  # Is this a package object?
  PACKAGE=$PACKAGE`grep "package object" $f | head -n 1 |
    perl -e 'my $l = <>; $l =~ m/package object\s*([a-zA-Z0-9]*)/; print ($1 eq "" ? "" : "."); print $1."\n";'`
  PACKAGEDIR=`echo $PACKAGE | sed 's-\.-/-g'`

  echo "Moving ${f##*/} to package $PACKAGE ($PACKAGEDIR)"

  if [ ! -d $PACKAGEDIR ]; then
    mkdir -p $PACKAGEDIR
  fi

  mv $f $PACKAGEDIR
done
