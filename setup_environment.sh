#!/bin/bash -eux

VENV_DIR=`pwd`/venv
PIP=$VENV_DIR/bin/pip
PACKAGES='
    pony
    selenium
    lxml
'

function make_venv() {
    mkdir $VENV_DIR
    virtualenv -p `which python2.7` --prompt="collector" \
        --no-site-packages $VENV_DIR
}

function install_packages() {
    sudo apt install python2.7-dev libssl-dev \
        libxslt-dev libxml2-dev

    sudo apt install libpython2.7-stdlib

    # use ./.node_modules/.bin in $PATH for phantomjs
    #npm install phantomjs

    for package in $PACKAGES; do
        $PIP install $package
    done
}


[ -e $VENV_DIR ] || make_venv
install_packages

#source $VENV_DIR/bin/activate
#deactivate
