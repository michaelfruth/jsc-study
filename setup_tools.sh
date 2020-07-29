#!/bin/zsh

installJsonsubschema() {
  ECHO "Install jsonsubschema"
  git clone https://github.com/IBM/jsonsubschema.git tools/jsonsubschema
  git --git-dir=./tools/jsonsubschema/.git checkout 165f8939c9c294d8f6fa01d9e6690a26bd24e9c9
}

installIsJsonSchemaSubset() {
  ECHO "Install IsJsonSchemaSubset"
  npm install --prefix ./tools/npm-is-json-schema-subset
}

installJsonSchemaDiffValidator() {
  ECHO "Install JsonSchemaDiffValidator"
  npm install --prefix ./tools/npm-json-schema-diff-validator
}

installJsonsubschema
installIsJsonSchemaSubset
installJsonSchemaDiffValidator

pipenv update