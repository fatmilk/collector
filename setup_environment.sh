#!/bin/bash -eux

VENV_DIR=`pwd`/venv
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
    # sudo apt install python2.7-dev
    npm install -g phantomjs

    for package in $PACKAGES; do
        pip install $package
    done
}


[ -e $VENV_DIR ] || make_venv
source $VENV_DIR/bin/activate
install_packages
deactivate
