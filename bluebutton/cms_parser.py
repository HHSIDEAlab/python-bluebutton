#!/usr/bin/env python
"""
python-bluebutton
FILE: cms_parser
Created: 3/3/15 12:16 PM

convert CMS BlueButton text to json

"""
__author__ = 'Mark Scrimshire:@ekivemark'


import json
import re
import os, sys
from datetime import datetime, date, timedelta

import collections


# divider = "--------------------------------"
divider = "----------"

# Seg is used to control and translate headings and lines
seg = [{"match": "mymedicare.GovPersonalHealthInformation",
        "pre": {"title": "MyMedicare.gov Personal Health Information",
            "languageCode": "code=\"en-US\"", "versionNumber": {"value": "3"},
            "effectiveTime": {"value": "20150210171504+0500"},
            "confidentialityCode": {"code": "N", "codeSystem": "2.16.840.1.113883.5.25"},
            "originator": "MyMedicare.gov"},
        "level": 0,
        "name": "header",
        "this_entry": "",
        "content": "dict",
        "multi": "False",
        "parent": "",
        "file_source": "CMS",
        },
    {"match": "demographic",
     "pre": {},
     "level": 0,
     "name": "patient",
     "content": "dict",
     "mode": "",
     "multi": "False",
     "parent": "",
     "file_source": "CMS",
     },
    {"match": "emergencyContact",
     "pre": {},
     "level": 0,
     "name": "emergencyContact",
     "type": "list",
     "mode": "",
     "multi": "True",
     "parent": "",
     "file_source": "CMS",
    },
    {"match": "emergencyContact.contactName",
     "pre": {},
     "level": 1,
     "list": True,
     "name": "name",
     "end_match": "emailAddress",
     "type": "dict",
     "mode": "block",
     "dict_name": "",
     "multi": "False",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.addressType",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "block",
     "dict_name": "address",
     "multi": "False",
     "name": "type",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.addressLine1",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "block",
     "dict_name": "address",
     "multi": "False",
     "name": "line1",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.addressLine2",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "block",
     "dict_name": "address",
     "multi": "False",
     "name": "line2",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.city",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "block",
     "dict_name": "address",
     "multi": "False",
     "name": "city",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.state",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "block",
     "dict_name": "address",
     "multi": "False",
     "name": "state",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.zip",
     "pre": {},
     "level": 2,
     "type": "dict",
     "mode": "close",
     "dict_name": "address",
     "multi": "False",
     "name": "zip",
     "end_match": "zip",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.homePhone",
     "pre": {},
     "level": 2,
     "type": "dict",
     "dict_name": "phone",
     "mode": "block",
     "multi": "False",
     "name": "home",
     "field": "home",
     "end_match": "mobilePhone",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.workPhone",
     "pre": {},
     "level": 2,
     "type": "dict",
     "dict_name": "phone",
     "mode": "block",
     "multi": "False",
     "name": "work",
     "field": "work",
     "end_match": "mobilePhone",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },
    {"match": "emergencyContact.mobilePhone",
     "pre": {},
     "level": 2,
     "type": "dict",
     "dict_name": "phone",
     "mode": "close",
     "multi": "False",
     "name": "mobile",
     "field": "mobile",
     "end_match": "mobilePhone",
     "parent": "emergencyContact",
     "file_source": "CMS",
     },

    {"match": "selfReportedMedicalConditions", "name": "medicalConditions"},
    {"match": "selfReportedAllergies", "name": "Allergies"},
    {"match": "selfReportedImplantableDevice", "name": "ImplantableDevices"},
    {"match": "selfReportedImmunizations", "name": "Immunizations"},
    {"match": "selfReportedLabsAndTests", "name": "Labs"},
    {"match": "selfReportedVitalStatistics", "name": "vitals"},
    {"match": "familyMedicalHistory", "name": "familyHistory"},
    {"match": "drugs", "name": "medications"},
    {"match": "preventiveServices", "name": "preventiveServices"},
    {"match": "providers", "name": "providers"},
    {"match": "pharmacies", "name": "pharmacies"},
    {"match": "plans", "name": "insurance", "type": "list"},
    {"match": "employerSubsidy", "name": "category", "level": 1},
    {"match": "primaryInsurance", "name": "category", "level": 1},
    {"match": "otherInsurance", "name": "category", "level": 1},
    {"match": "claimSummary", "name": "claims", "type": "list",
     "level": 0},
    {"match": "claimHeader", "name": "claim", "type": "dict",
     "level": 1},
    {"match": "claimLinesForClaimNumber", "name": "details",
     "type": "list", "level": 2, "multi": "True"},
    ]

# TODO: define all field translations in seg[]
# TODO: Assign level to each field. Start with base 0


fld_tx = [{"input":"Emergency Contact","output":"emergency_contact"},
    {"input":"emergency_contact.Contact Name","output":"name"},
    {"input":"emergency_contact.Address Line 1","output":"line_1"},
    {"input":"emergency_contact.Address Line 2","output":"line_2"},
    ]

def cms_file_parse2(inPath):
    # Parse a CMS BlueButton file (inPath)

    # Set default variables on entry
    k = ""
    v = ""
    items=collections.OrderedDict()

    first_header = True
    header_line = True
    get_title = False
    skip = False
    line_type = "Body"
    multi = False
    skip = False

    segment_source = ""
    match_key = {}
    match_string = ""

    current_segment = ""
    previous_segment = current_segment
    header_block = {}
    block_info = {}

    line_list = []
    segment_dict = collections.OrderedDict()
    sub_segment_dict = collections.OrderedDict()
    sub_segment_list = []

    # Open the file for reading
    with open(inPath, 'r') as f:
        # get the line from the input file
        for i, l in enumerate(f):
            # reset line_dict
            # line_dict = collections.OrderedDict()

            # remove blanks from end of line
            l = l.rstrip()

            # print "![", i, ":", line_type, ":", l, "]"
            if line_type == "Body" and (divider in l):
                # This should be the first divider line in the header
                header_line = True
                get_title = True
                line_type = "Header"
                if not first_header:
                    # we want to write out the previous segment
                    # print i, ":Write Previous Segment"
                    # print i, ":1st Divider:", l
                    ####################
                    # Write segment here
                    ####################
                    # print i, "Cur_Seg:", current_segment, ":", multi
                    #if multi:
                    #    print line_list
                    # write source: segment_source to segment_dict
                    segment_dict["source"] = segment_source
                    #
                    items, segment_dict, line_list = write_segment(items, current_segment, segment_dict, line_list, multi)
                    # Reset the Dict
                    segment_dict = collections.OrderedDict()
                    line_list = []
                    multi = False
                    ####################
                    first_header = False
                else:
                    # at top of document so no previous segment
                    first_header = False
                    # print i,":1st Divider:",l

            elif line_type == "Header" and header_line and get_title:
                # Get the title line
                # print "we found title:",l
                # print i, "[About to set Seg:", l, "]"
                # Save the current_segment before we overwrite it
                if not (divider in l):
                    if len(l.strip()) > 0:
                        # print "title length:", len(l.strip())

                        # TODO: remove : from Title - for Claims LineNumber:
                        titleline = l.split(":")
                        tl = titleline[0].rstrip()

                        previous_segment = current_segment
                        header_block = get_segment(headlessCamel(tl))
                        # print headlessCamel(l), "translated:", header_block

                        if len(header_block) > 1:
                            current_segment = header_block["name"]
                        else:
                            current_segment = headlessCamel(tl)
                        if find_segment(headlessCamel(tl)):
                            # print "Segment list: %s FOUND" % l
                            # Get a dict for this segment
                            header_block = get_segment(headlessCamel(tl))
                            multi = multi_item(header_block)
                            header_block_level = get_header_block_level(header_block)

                            # update the match_key
                            match_key[header_block_level] = current_segment

                            line_list = []
                            k = header_block["name"]

                            # print i, k, ":Multi:", multi

                            # print "k set to [%s]" % k
                            current_segment, segment_dict = segment_prefill(header_block)

                        # print "Current_Segment:", current_segment
                        # print "%s%s%s" % ('"', headlessCamel(l), '"')
                        get_title = False
                        # print i, ":Set segment:", current_segment, "]"
                else:
                    # we didn't find a title
                    # So set a default
                    # Only claim summary title segments are blank
                    # save current_segment
                    previous_segment = current_segment
                    current_segment = "claimHeader"
                    # print "set title to", current_segment
                    # print i,"We never got a title line...", current_segment
                    header_line = False
                    line_type = "Body"

                # Write the last segment and reset



            elif line_type == "Header" and (divider in l):
                # this should be the closing divider line
                # print "Closing Divider"
                header_line = False
                line_type = "Body"

            else:
                # TODO: Convert date fields to ISO8601 format
                # TODO: Test for date field using "date" in Key

                line_type = "Body"

                # split on the : in to key and value
                line = l.split(":")
                if len(line) > 1:
                    # Assign line[0] to k and format as headlessCamel
                    k = headlessCamel(line[0])
                    v = line[1].lstrip()
                    v = v.rstrip()

                    #
                    # Now we deal with some special items.
                    # The Date and time in the header section
                    if k[2] == "/":
                        v = {"value": parse_time(l)}
                        k = "effectiveTime"
                        # print i, ":", l
                        # print i, "got date for:", current_segment, k, ":", v

                        segment_dict[k] = v


                    elif k.upper() == "SOURCE":
                        segment_source=set_source(segment_source, k, v)
                        # Apply headlessCamelCase to K
                        k = headlessCamel(k)
                        v = segment_source
                        # print i, "set source in:", current_segment, ":", k, ":", v

                        segment_dict[k] = v

                    else:
                        # match key against segment
                        match_string = current_segment + "." + k

                        print "Match with:", match_string

                        if find_segment(match_string):
                            # Get info about how to treat this key
                            # first we need to construct the field key to
                            # lookup in seg list

                            block_info = get_segment(match_string)

                            k = block_info["name"]
                            # print i, ":k:", k, ":", block_info
                            if block_info["mode"] == "block":
                                skip = True
                                if block_info["type"] == "dict":
                                    sub_segment_dict[block_info["name"]] = v
                                elif block_info["type"] == "list":
                                    sub_segment_list.append({k: v})
                                else:
                                    sub_segment[block_info["name"]] = v

                            elif block_info["mode"] == "close":
                                skip = True
                                if block_info["type"] == "dict":
                                    sub_segment_dict[block_info["name"]] = v
                                    segment_dict[block_info["dict_name"]] = sub_segment_dict
                                    sub_segment_dict = collections.OrderedDict()

                                elif block_info["type"] == "list":
                                    sub_segment_list.append({k: v})
                                    segment_dict[block_info["dict_name"]] = sub_segment_list
                                    sub_segment_list = []
                                else:
                                    segment_dict[block_info["name"]] = v


                        if multi:
                            # Add Source value to each block
                            segment_dict["source"] = segment_source
                            # print "Line_List:[", line_list, "]"
                            # print "Segment_dict:[", segment_dict, "]"
                            if (k in segment_dict):
                                line_list.append(segment_dict)
                                segment_dict = collections.OrderedDict()

                        if not skip:
                            segment_dict[k] = v
                        skip = False
                    # print "B[", i, ":", line_type, ":", l, "]"


            # ===================
            # Temporary Insertion
            # if i > 80:
            #    break
            # end of temporary insertion
            # ===================



    f.close()

    # write the last segment
    # print "Writing the last segment"
    items, segment_dict, line_list = write_segment(items, current_segment, segment_dict, line_list, multi)

    return items

def cms_file_parse(inPath):
    # Parse a CMS BlueButton file (inPath)
    # Using a redefined Parsing process

    # Set default variables on entry
    k=""
    v=""
    items=collections.OrderedDict()
    first_header=True
    header_line=True
    get_title=False

    line_type="Header"
    segment_dict=collections.OrderedDict()
    current_segment=""
    segment_source=""
    previous_segment=current_segment
    line_dict=collections.OrderedDict()

    # Open the file for reading
    with open(inPath, 'r') as f:
        # get the line from the input file
        for i, l in enumerate(f):
            l = l.rstrip()

            line = l.split(":")
            if len(line) > 1:
                k = line[0]
                v = line[1].lstrip()
                v = v.rstrip()

            if len(l) <= 1 and header_line == False:
                # The line is a detail line and is empty so ignore it and move on to next line
                #print "empty line %s[%s] - skipping to next line" % (i,l)
                continue

            if header_line:
                line_type = "Header"
            else:
                line_type = "Body"

            # From now on We are dealing with a non-blank line

            # Segment titles are wrapped by lines of minus signs (divider)
            # So let's check if we have found a divider

            if (divider in l) and not header_line:
                # We have a divider. Is it an open or closing divider?
                header_line=True
                get_title=True
                # First we need to write the old segment out
                if first_header:
                    # file starts with a header line but
                    # there is nothing to write
                    first_header=False
                    #print "First Header - Nothing to write"
                    continue
                else:
                    # not the first header so we should write the segment
                    #print "Not First Header - Write segment"
                    print i,"writing segment",
                    items, segment_dict = write_segment(items, current_segment, segment_dict)
                    # Then we can continue
                    continue

            #print "HL/GT:",header_line,get_title
            if header_line and get_title:
                if not (divider in l):
                    previous_segment = current_segment
                    # assign title to current_segment
                    current_segment = k.lower().replace(" ", "_")
                    get_title = False

                else:
                    # blank lines for title were skipped so we hit divider
                    # before setting current_segment = title
                    # So set to "claim_summary" since this is only unnamed segment
                    current_segment = "claim_summary"
                    get_title = False

                #print "Header:",current_segment
                # now match the title in seg["key"]
                # and write any prefill information to the segment
                if find_segment(k):
                    # Check the seq list for a match
                    #print "Segment list: %s FOUND" % l
                    seg_returned = get_segment(k)
                    k = seg_returned["name"]
                    #print "k set to [%s]" % k

                    current_segment, segment_dict = segment_prefill(seg_returned)

                    # print "segment_dict: %s" % segment_dict
                else:
                    # We didn't find a match so let's set it to "Other"
                    current_segment = k.lower().replace(" ", "_")
                    segment_dict = collections.OrderedDict()
                    segment_dict[current_segment] = {}

                print "%s:Current_Segment: %s" % (i, current_segment)
                #print "Header Line:",header_line
                # go to next line in file
                continue

            print "[%s:CSeg:%s|%s L:[%s]" % (i,current_segment,line_type,l)

            #print "%s:Not a Heading Line" % i
            ######################################
            # Lines below are detail lines

            # Need to lookup line in fld_tx to translate k to preferred string
            # if no match in fld_tx then force to lower().replace(" ","_")

            # Need to evaluate content of line to determine if
            # dict, list or text needs to be processed

            # add dict, list or text with key to segment_dict

            # Let's check for Source and set that up

            # ========================
            # temporary insertion to skip detail lines
            #continue
            # ========================
            if current_segment == "header":
                # Now we deal with some special items.
                # The Date and time in the header section
                if k[2] == "/":
                    # print "got the date line"
                    v = {"value": parse_time(l)}
                    k = "effectiveTime"
                    segment_dict[current_segment]={k:v}
                    continue
            segment_source=set_source(segment_source,k,v)
            if k.upper()=="SOURCE":
                k=k.lower()
                v=segment_source
                segment_dict[current_segment]={k:v}
                continue

            line_dict[k]=v

            # print "line_dict:", current_segment,":", line_dict

            segment_dict[current_segment]=line_dict

            # reset the line_dict
            line_dict=collections.OrderedDict()

        # end of for loop

    f.close()
    # write the last segment
    #print "Writing the last segment"
    items, segment_dict = write_segment(items, current_segment, segment_dict)

    return items


def headlessCamel(In_put):
    # Use this to format field names:
    # Convert words to title format and remove spaces
    # Remove underscores
    # Make first character lower case
    # result result

    Camel = ''.join(x for x in In_put.title() if not x.isspace())
    Camel = Camel.replace('_', '')
    result = Camel[0].lower() + Camel[1:len(Camel)]

    # print "headlessCamel:", result
    return result

def set_header_line(hl):
    # flip header_line value. received as hl (True or False)

        return (not hl)


def write_segment(itm, sgmnt, sgmnt_dict, ln_list, multi):
    # Write the segment to items dict
    # print "Writing Segment:", sgmnt
    # print "Adding:", sgmnt_dict

    # print "============================"
    # print "Writing Seg:",sgmnt
    # print "============================"
    # print "Writing dict:"
    # print sgmnt_dict
    # print "============================"
    if multi:
        ln_list.append(sgmnt_dict)
        print "Multi List:", ln_list
        itm[sgmnt] = ln_list
    else:
        itm[sgmnt] = sgmnt_dict

    return itm, sgmnt_dict, ln_list


def get_segment(title):

    result = {}
    # cycle through the seg dictionary to match against title
    for ky in seg:
        if title in ky["match"]:
            result = ky
            break

    return result

def find_segment(title):

    result = False
    for ky in seg:
        # print k
        if title in ky["match"]:
            # print "Match: %s : %s" % (title, ky['key'])
            result = True
            break

    return result

def parse_time(t):
    # convert time to  json format
    t = t.strip()
    time_value = datetime.strptime(t, "%m/%d/%Y %I:%M %p")
    # print time_value
    return_value = time_value.strftime("%Y%m%d%H%M%S+0500")

    # print return_value
    return return_value

def segment_prefill(seg):
    # Receive the Segment information for a header line
    # get the seg["pre"] and iterate through the dict
    # assigning to segment_dict
    # First we reset the segment_dict as an OrderedDict
    segment_dict = collections.OrderedDict()

    # print seg

    current_segment = seg["name"]
    if "pre" in seg:
        pre = seg["pre"]
        # print pre
        for pi, pv in pre.iteritems():
            # print pi,":" ,pv
            segment_dict[pi] = pv

    return current_segment, segment_dict

def set_source(current_source, key, value):
    # Set the source of the data

    if key.upper() == "SOURCE":
        result = ""
        # print "Found Source: [%s:%s]" % (key,value)
        if value.upper() == "SELF-ENTERED":
            result = "patient"
        elif value.upper() == "MYMEDICARE.GOV":
            result = "MyMedicare.gov"
        else:
            result = value.upper()
        # print "[%s]" % result
        return result
    else:
        return current_source

def multi_item(seg):
    # check for "multi" in seg dict
    # If multi line = "True" set to True
    # use line_list instead of dict to allow multiple entries
    multi = False
    if "multi" in seg:
        if seg["multi"] == "True":
            multi = True

        # print "Multi:", multi
    return multi

def build_key(mk, bi):
    # update make_key using content of build_info
    lvl = bi["level"]
    mk[lvl] = bi["name"]

def get_header_block_level(header_block):

    lvl = 0
    if "level" in header_block:
        lvl = header_block["level"]

    return lvl