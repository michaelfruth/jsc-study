# SPDX-License-Identifier: GPL-2.0-only
#
# Replication package for EmpER 2021
# Challenges in Checking JSON Schema Containment over Evolving Real-World Schemas
#
# Authors:
#   Copyright 2021, Michael Fruth <michael.fruth@uni-passau.de>
#   Copyright 2021, Mohamed-Amine Baazizi
#   Copyright 2021, Dario Colazzo
#   Copyright 2021, Giorgio Ghelli
#   Copyright 2021, Carlo Sartiani
#   Copyright 2021, Stefanie Scherzinger <stefanie.scherzinger@uni-passau.de>

FROM python:3.7

MAINTAINER Michael Fruth <michael.fruth@uni-passau.de>

ENV DEBIAN_FRONTEND noninteractive
ENV LANG="C"
ENV LC_ALL="C"

########################
# Installation
########################
RUN apt-get update -qq
RUN apt-get install -y --no-install-recommends \
    git \
    npm
RUN pip install pipenv


########################
# Infrastructure
########################
RUN useradd -m -G sudo -s /bin/bash repro && echo "repro:repro" | chpasswd
USER repro
WORKDIR /home/repro

########################
# Add files
########################
COPY --chown=repro:repro . /home/repro/jsc-study


########################
# Prepartion for JSC-Study
########################
WORKDIR /home/repro/jsc-study
RUN ./setup_tools.sh

# Fix greenery because of breaking changes. Do not use the latest version.
RUN pipenv uninstall greenery && pipenv install greenery==3.3.7

# Change entrypoint, otherwise python shell is entrypoint.
ENTRYPOINT /bin/bash 

