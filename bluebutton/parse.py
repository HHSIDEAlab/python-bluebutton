#!/usr/bin/env python
"""
convert bluebutton to json
"""

import json
import re
import os, sys
from datetime import datetime, date, timedelta

import collections

#inPath="va_sample_file.txt"
#OutPath="va_sample_file.json"

sections=("MYMEDICARE.GOV PERSONAL HEALTH INFORMATION",
"DEMOGRAPHIC",
"MY HEALTHEVET PERSONAL HEALTH INFORMATION",
"MY HEALTHEVET ACCOUNT SUMMARY",
"DEMOGRAPHICS",
"ALLERGIES/ADVERSE REACTIONS",
"MEDICAL EVENTS",
"IMMUNIZATIONS",
"FAMILY HEALTH HISTORY", 
"MILITARY HEALTH HISTORY",
"VA MEDICATION HISTORY",
"MEDICATIONS AND SUPPLEMENTS",
"VA WELLNESS REMINDERS",
"VITALS AND READINGS"
)

section_info=[{"MYMEDICARE.GOV PERSONAL HEALTH INFORMATION":{"title": "MyMedicare.gov Personal Health Information",
            "languageCode": "code=\"en-US\"",
            "versionNumber": {"value": "3"},
            "effectiveTime": {"value": "20150210171504+0500"},
            "confidentialityCode": {"code": "N",
                                    "codeSystem": "2.16.840.1.113883.5.25"},
            "originator": "MyMedicare.gov"}},
              ]

#divider="--------------------------------"
divider = "----------"
vitals= ("Blood pressure", "Body weight")

# Redefine the Parsing process
# get the line from the input file
# reset the generic_dict to blank
# is_header (ie. the line doesn't have a ":")
# if is_header
#   Match header.upper() against segment.header.upper() entries
#       if matched
#          get segment.prefill_content for segment
#          get segment.level (ie. header = 0)
#          get segment.name
#          get segment.key_match_end
#          get segment.prefix
# else
#   split line by ":" to key and val
#   Match segment.prefix.upper()+key.upper() against body.header.upper()
#       if matched
#          get body.prefill_content for key
#          get body.level (ie. level of dict embed)
#          get body.name
#          get body.key_match_end
#   Deal with special case content
#   eg. date inside header (key[2]="/")
#          reset key and val
#          format date
#   Match segment.prefix.upper()+key.upper() against field.name
#          reset key with field.name
#
#   write the generic_dict with [key]=val
#   write section[level]=generic_dict




def age(dob):
    import datetime
    today = datetime.date.today()

    if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
        return today.year - dob.year - 1
    else:
        return today.year - dob.year


def simple_parse(inPath):
    line=[]
    items=[]
    generic_dict=collections.OrderedDict()
    with open(inPath, 'r') as f:
        for i, l in enumerate(f):
            generic_dict={}  
            line=l.split(":")
            if len(line)>1:
                k=line[0]
                v=line[1]
                if len(k)>1:
                    # do we have a date and time
                    k = "Date"

                if v[0]==" ":
                    v=v.lstrip()
                if len(line)>2 and k=="Time":
                    v="%s:%s" % (line[1], line[2])
                v=v.rstrip()
                generic_dict[k]=v

                items.append(generic_dict)	
    f.close()
    return items


def section_parse(inPath):
    #print "in Section Parse"
    line=[]
    items=[]
    generic_dict=collections.OrderedDict()
    segments=collections.OrderedDict()
    segment_open=False
    current_segment=""
    segment_dict = collections.OrderedDict()
    segment_source=""

    with open(inPath, 'r') as f:
        for i, l in enumerate(f):
            generic_dict = {}
            # print "input: %s" % l
            line=l.split(":")
            if len(line)>1:
                k=line[0]
                v=line[1]
                print "Line %s: %s" % (i, line)
                if v[0]==" ":
                    v=v.lstrip()
                v=v.rstrip()
                segment_source=set_source(segment_source,k,v)
                if k.upper()=="SOURCE":
                    v=segment_source
                if current_segment=="header":
                    if k[2]=="/":
                        print "got the date line"
                        v = {"value": parse_time(l)}
                        k = "effectiveTime"
                generic_dict[k]=v
                segment_dict[k]=v
                segments.update({current_segment : segment_dict})
                #print "Segments-current_segment: %s" % current_segment
                #print segments[current_segment]
                #print "*******"

            else:
                #print "Line: %s Not processed" % i
                if divider in l:
                    if segment_open:
                        segment_open=False
                    else:
                        segment_open=True
                if (divider not in l) and (segment_open==True):
                    l=l.strip()
                    if len(l)<=1:
                        l="Claim"
                    current_segment, segment_dict = segment_evaluation(l.strip())


    f.close()
    return segments

def parse_time(t):
    # convert time to  json format
    t = t.strip()
    time_value = datetime.strptime(t, "%m/%d/%Y %I:%M %p")
    #print time_value
    return_value = time_value.strftime("%Y%m%d%H%M%S+0500")
    #print return_value
    return return_value

def segment_evaluation(input_line):
    # check for section and load in any pre-defined values to the dict
    segment_dict = collections.OrderedDict()
    if input_line=="MYMEDICARE.GOV PERSONAL HEALTH INFORMATION":
        current_segment = "header"
        segment_dict["title"] = input_line
        segment_dict["languageCode"] = "code=\"en-US\""
        segment_dict["versionNumber"] = {"value":"3"}
        segment_dict["effectiveTime"] = {}
        segment_dict["confidentialityCode"] = {"code": "N","codeSystem": "2.16.840.1.113883.5.25"}
        segment_dict["originator"] = "MyMedicare.gov"
    else:
        current_segment = input_line

    return current_segment, segment_dict


def set_source(current_source,key,value):
    # Set the source of the data

    if key.upper() == "SOURCE":
        result = ""
        print "Found Source: [%s:%s]" % (key,value)
        if value.upper() == "SELF-ENTERED":
            result = "patient"
        elif value.upper() == "MYMEDICARE.GOV":
            result = "MyMedicare.gov"
        else:
            result = value.upper()
        print "[%s]" % result
        return result
    else:
        return current_source



def build_bp_readings(items):

    bpdictlist=[]
    i=0
    for it in items:
        if it.has_key("Measurement Type"):
            if it['Measurement Type']=="Blood pressure":
                """The next 4 lines are date time systolic and diastolic"""
                bpdict={}
                bpdict.update(items[i+1])
                bpdict.update(items[i+2])
                bpdict['bp']="bp=%s/%s" % (items[i+3]['Systolic'], items[i+4]['Diastolic'])
                bpdict['bp_sys']=items[i+3]['Systolic']
                bpdict['bp_dia']=items[i+4]['Diastolic']
                bpdictlist.append(bpdict)
        i+=1
    return bpdictlist

def build_wt_readings(items):

    wtdictlist=[]
    i=0
    for it in items:
        if it.has_key("Measurement Type"):
            if it['Measurement Type']=="Body weight":
                """The next 4 lines are date time systolic and diastolic"""
                wtdict={}
                wtdict.update(items[i+1])
                wtdict.update(items[i+2])
                wtdict['wt']="wt=%sl" % (items[i+3]['Body Weight'])
                wtdictlist.append(wtdict)
        i+=1
    return wtdictlist

def build_mds_readings(items):
    print "here"
    mdsdictlist=[]
    i=0
    for it in items:
        if it.has_key("Medication"):
            mdsdict={}
            mdsdict.update(items[i])
            j=0
            while not items[i+j].has_key('Prescription Number'):
                print items[i+j]
                j+=1
                mdsdict.update(items[i+j])
                mdsdictlist.append(mdsdict)
        i+=1
    return mdsdictlist



def build_simple_demographics_readings(items):
    fnfound=False
    lnfound=False
    mifound=False
    gfound=False
    dobfound=False
    
    demodict={}
    for it in items:
        if it.has_key("First Name") and fnfound==False:
            demodict['first_name']=it['First Name']
            fnfound=True
        
        if it.has_key("Middle Initial") and mifound==False:
            demodict['middle_initial']=it['Middle Initial']
            mifound=True    
    
        if it.has_key("Last Name") and lnfound==False:
            demodict['last_name']=it['Last Name']
            lnfound=True
            
        if it.has_key("Gender") and gfound==False:
            
            g=it['Gender'].split(" ")
            demodict['gender']=g[0]
            gfound=True
    
        if it.has_key("Date of Birth") and dobfound==False:
            (m, d, y)=it['Date of Birth'].split("/")
            demodict['date_of_birth']=it['Date of Birth']
            dob=date(int(y),int(m),int(d))
            today = date.today()
            demodict['num_age']=age(dob)
            dobfound=True
    
    return demodict

def tojson(items):
    """tojson"""
    itemsjson = json.dumps(items, indent=4)
    return itemsjson

def write_file(write_dict,Outfile):
    f = open(Outfile, 'w')
    f.write(tojson(write_dict))
    f.close()

