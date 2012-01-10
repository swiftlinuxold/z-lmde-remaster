#!/bin/bash
# Proper header for a Bash script.

# Check for root user login
if [ ! $( id -u ) -eq 0 ]; then
	echo "You must be root to run this script."
	echo "Please enter su before running this script again."
	exit
fi

# Get your username (not root)
UNAME=$(awk -v val=1000 -F ":" '$3==val{print $1}' /etc/passwd)
DIR_DEVELOP=/home/$UNAME/develop

# Obtain MintConstructor, the package for creating the Linux Mint ISO file
apt-get install -y mintconstructor 

FILE1=$DIR_DEVELOP/remaster/usr_lib_linuxmint_mintConstructor/mintConstructor.py
FILE2=/usr/lib/linuxmint/mintConstructor/mintConstructor.py
cp $FILE1 $FILE2
chmod a+x $FILE2

python $FILE2
