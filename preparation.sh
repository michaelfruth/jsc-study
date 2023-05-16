#!/bin/bash

echo "Cloning schemastore..."
git clone https://github.com/SchemaStore/schemastore schemastore
git -C ./schemastore c48c7275ff2911918af164cde850ec822529e5d3

echo "Cloning each commit into a own directory..."
pipenv run python git_history_cloner.py -g schemastore -od schemastore_history

