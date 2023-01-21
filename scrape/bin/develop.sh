#!/bin/bash
cd "$(dirname "$0")"
cd ..

nodemon -w 'python/' -e py -x 'python -m python.scrape'