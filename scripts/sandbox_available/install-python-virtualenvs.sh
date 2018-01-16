#!/bin/bash
#
# Looks for *-requirements.txt files in the sandbox directories and creates
# virtual environments for them. The name of the virtual environment is the
# beginning part of the requirements file name. The first line of the
# requirements file should define the python version in a comment.
#
#    selenium_example-requirements.txt:
#        # python3.4
#        selenium==2.47.1
#        html5lib
#
VDIR=/usr/local/pyvirtualenvs

# Check directory to store virtual environments.
mkdir -p $VDIR
cd $VDIR

# Create virtual environments.
for path in $(find /usr/local/sandbox -name \*-requirements.txt); do
	file=${path##*/}
	name=${file%-requirements.txt}

	line=`head -1 $path`
	python=${line##* }
	if [[ "$python" != "python"* ]]; then
		python="python"
	fi

	if [ ! -d $name ]
	then
		virtualenv -p $python $name
	fi
	source $name/bin/activate
	pip install --upgrade pip
	pip install -r $path
	deactivate
done
