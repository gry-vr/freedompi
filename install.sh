#!/usr/bin/bash


# now we must do stuff
#
# USAGE
# running this script should look something like ./install.sh canlink
# or like ./install.sh companionpi
#
# An exhaustive list of stuff that needs to happen. in order:
#
# HARDWARE DEPENDENCIES
# necessary libraries must be installed for the CAN HAT
# config.txt must be set up to support the CAN HAT
#
#
#
# SOFTWARE DEPENDENCIES
#
# now depending on what function the pi will be serving ( canlink or companion )
# 
# CANLINK:
#   - download and install canlink software
#   - set up the startup service. 
#
# COMPANION:
#   -must ensure that python, pip, and virtual environments work correctly
#   -python scripts need to be placed in the correct location.
#   -then pip install all the necessary python packages that are script dependencies
#   
# 
