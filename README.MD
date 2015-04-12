
# BlueButton Parser

(c.) Alan Viars - Videntity Systems Inc. - 2011

(c.) Mark Scrimshire - CMS - 2015

Version 0.9.1 (CMS BlueButton JSON Generator)

This library is dual licensed.  It is released under the GPL licnese 
agreement and under a commercial license by Videntity systems Inc.

Added CMS BlueButton Parser to convert Medicare BlueButton v2.0 to format
that is partially compliant with CMS BlueButton 3.0 JSON Format

Status: released. Converts CMS Medicare BlueButton v2.0 file to JSON.

use command line:

python bbp.py CMSFILE {input file} {output file}

For CMS BlueButton file format information refer to:
https://github.com/ekivemark/claims

## Installation
===============

Use pip to install the parser.
::
    pip install python-bluebutton

## Converting a CMS BlueButton File
### 1. Login to http://MyMedicare.gov
### 2. Access the BlueButton feature
### 3. Download your BlueButton as a text file
### 4. Run the Python-BlueButton Parser:

To run the Python-BlueButton Parser we will make the following assumptions. You can adapt these to your system, 

#### a) It is assumed that python is installed on your system can be run from any directory. 

#### b) Your system allows you to refer to your home folder using ~ (tilde sign) 

#### c) You downloaded the BlueButton text file to your /Downloads Folder as BlueButton.txt 

#### d) You want to save the output file from the parser utility to your /Desktop folder as text_json.txt 

#### e) You installed the Python-BlueButton code to the BBParser folder off the root directory of your system


Execute the following command:

python /BBParser/bluebutton/bbp.py CMSFILE ~/Downloads/BlueButton.txt ~/Desktop/BlueButton.txt


Using the Parser
================

Here is another simple example using a VA BlueButton Text File:
::
    # Import the library
    >>> from bluebutton.parse import *
    
    # Open and parse the bluebutton file.
    >>> parsed = simple_parse("va_sample_file.txt")
    

    # Get the bloodpressure readings
    >>> build_bp_readings(parsed)
    
    [{'Date': '08/02/2010', 'bp_sys': '141', 'bp_dia': '76', 'bp': 'bp=141/76', 'Time': ' 17:30'}, {'Date': '08/02/2010', 'bp_sys': '150', 'bp_dia': '76', 'bp': 'bp=150/76', 'Time': ' 17:20'}]
    
    # Get the weight readings
    >>> build_wt_readings(parsed)
    
    [{'Date': '06/02/2010', 'wt': 'wt=242l', 'Time': ' 17:20'}, {'Date': '05/02/2010', 'wt': 'wt=244l', 'Time': ' 17:20'}, {'Date': '04/02/2010', 'wt': 'wt=246l', 'Time': ' 17:20'}]
    
    
    #Get demographics
    >>> build_simple_demographics_readings(parsed)
    
    {'middle_initial': 'A', 'first_name': 'ONE', 'last_name': 'MHVVETERAN', 'gender': 'Male', 'num_age': 64, 'date_of_birth': '03/01/1948'}
    
    #Convert demographics to JSON
    
    print tojson(build_simple_demographics_readings(parsed))
    
    {
    "middle_initial": "A", 
    "first_name": "ONE", 
    "last_name": "MHVVETERAN", 
    "gender": "Male", 
    "num_age": 64, 
    "date_of_birth": "03/01/1948"
    }

    # Get the medications
    >>> build_mds_readings(parsed)
    ...
    
    
