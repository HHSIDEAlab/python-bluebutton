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

from cms_parser_utilities import *
from cms_custom import *


# DBUG = False

divider = "----------"

def cms_file_read(inPath):
    # Read file and save in OrderedDict
    # Identify Headings and set them as level 0
    # Everything else assign as Level 1

    ln_cntr = 0
    blank_ln = 0
    f_lines = []
    set_level = 0

    line_type = "BODY"
    header_line = False
    set_header = "HEADER"
    current_segment = ""

    line_dict = {}

    with open(inPath, 'r') as f:
        # get the line from the input file
        # print "Processing:",
        for i, l in enumerate(f):
            # reset the dictionary
            line_dict = {}

            # Read each line in file
            l = l.rstrip()
            # remove white space from end of line

            # if (i % 10) == 0:
                # print ".",
                # Show progress every 10 steps

            if len(l) < 1:
                # skip blank lines
                blank_ln += 1
                continue

            if line_type == "BODY" and (divider in l):
                header_line = True
                get_title = True
                line_type = "HEADER"
                blank_ln += 1
                continue
            elif line_type == "HEADER" and header_line and get_title:
                # Get the title line
                # print "we found title:",l
                # print i, "[About to set Seg:", l, "]"
                # Save the current_segment before we overwrite it
                if not (divider in l):
                    if len(l.strip()) > 0:
                        # print "title length:", len(l.strip())

                        # Remove : from Title - for Claims LineNumber:
                        titleline = l.split(":")
                        tl = titleline[0].rstrip()
                        set_header = line_type
                        current_segment = tl
                        get_title = False
                        if "Claim Lines for Claim Number" in l:
                            set_level = 1
                            # set_header = "BODY"
                        else:
                            set_level = 0
                else:
                    # we didn't find a title
                    # So set a default
                    # Only claim summary title segments are blank
                    # save current_segment
                    previous_segment = current_segment
                    current_segment = "claim Header"
                    # print "set title to", current_segment
                    # print i,"We never got a title line...",
                    # current_segment
                    set_level = 1
                    header_line = False
                    if current_segment == "claim Header":
                        # set_header = "BODY"
                        set_header = "HEADER"
                    else:
                        set_header = "HEADER"
                    line_type = "BODY"

                line_dict = {"key": ln_cntr,
                             "level": set_level,
                             "line": current_segment,
                             "type": set_header}

            elif line_type == "HEADER" and not get_title:
                # we got a second divider
                if divider in l:
                    set_header = "BODY"
                    line_type = "BODY"
                    header_line = False

                    blank_ln += 1
                    continue

            else:
                line_type = "BODY"
                set_header = line_type

                line_dict = {"key": ln_cntr,
                             "level": set_level + 1,
                             "line": l,
                             "type": set_header}

            f_lines.append({ln_cntr: line_dict})

            ln_cntr += 1

    f.close()

    # print i+1, "records"
    # print ln_cntr, "written."
    # print blank_ln, "skipped"

    # print f_lines
    # print ""

    return f_lines


def parse_lines(ln_list):
    # Receive list created in cms_file_read
    # Build the final Json dict
    # Use SEG_DEF to control JSON construction

    # set variables

    DBUG = False

    ln = {}
    ln_ctrl = {}

    hdr_lk_up = ""
    seg_match_exact = True
    # Pass to get_segment for an exact match

    match_ln = [None, None, None, None, None, None, None, None, None, None]

    segment_dict = collections.OrderedDict()
    out_dict = collections.OrderedDict()
    # Set starting point in list

    if DBUG:
        print "Initializing Working Storage Arrays...",

    block_limit = 9
    block = collections.OrderedDict()
    n = 0
    while n <= block_limit:
        block[n] = collections.OrderedDict()
        n += 1

    if DBUG:
        print "Done."

    i = 0

    # while i <= 44: #(len(ln_list)-1):
    while i <= (len(ln_list) - 1):
        # process each line in the list until end of list

        ln = get_line_dict(ln_list, i)

        wrk_lvl = ln["level"]

        match_ln = update_match(wrk_lvl,
                                headlessCamel(ln["line"]),
                                match_ln)

        match_hdr = combined_match(wrk_lvl, match_ln)

        hdr_lk_up = headlessCamel(ln["line"])

        if DBUG:
            do_DBUG("Line(i):", i, "ln:", ln,
                    "hdr_lk_up:", hdr_lk_up)

        # lookup ln in SEG_DEF

        if find_segment(hdr_lk_up, seg_match_exact):

            ln_ctrl = get_segment(hdr_lk_up, seg_match_exact)

            wrk_lvl = adjusted_level(ln["level"], match_ln)
            # We found a match in SEG_DEF
            # So we use SEG_DEF to tailor how we write the line and
            # section since a SEG_DEF defines special processing

            if DBUG:
                do_DBUG("CALLING PROCESS_HEADER===========================",
                        "i:", i,
                        "Match_ln:", match_ln,
                        "ln-ctrl:", to_json(ln_ctrl),
                        "ln_lvl:", ln["level"],
                        "wrk_lvl:", wrk_lvl)

            i, sub_seg, seg_name = process_header(i, ln_ctrl,
                                                  wrk_lvl,
                                                  ln_list)

            # Now load the info returned from process_header in out_dict
            out_dict[seg_name] = sub_seg[seg_name]

            if DBUG: # or True:
                do_DBUG("=============== RETURNED FROM PROCESS_HEADER",
                        "line:", i,
                        "ln_control:", ln_ctrl,
                        "seg_name:", seg_name,
                        "custom processing:", key_value("custom", ln_ctrl),
                        "sub_seg:", to_json(sub_seg))

            if key_value("custom", ln_ctrl) == "":
                # No custom processing required
                i, block_seg, block_name = process_subseg(i + 1,
                                                     ln_ctrl,
                                                     match_ln,
                                                     wrk_lvl,
                                                     ln_list,
                                                     sub_seg,
                                                     seg_name)

            elif key_value("custom", ln_ctrl) == "family_history":
                #custom processing required (ln_ctrl["custom"] is set)
                i, block_seg, block_name = custom_family_history(i + 1,
                                                                 ln_ctrl,
                                                                 match_ln,
                                                                 wrk_lvl,
                                                                 ln_list,
                                                                 sub_seg,
                                                                 seg_name)

            elif key_value("custom", ln_ctrl) == "claim_summary":
                #custom processing required (ln_ctrl["custom"] is set)
                i, block_seg, block_name = process_subseg(i + 1,
                                                          ln_ctrl,
                                                          match_ln,
                                                          wrk_lvl,
                                                          ln_list,
                                                          sub_seg,
                                                          seg_name)

            if DBUG:
                do_DBUG("---------------- RETURNED FROM PROCESS_BLOCK",
                        "ctr: i:", i, "block_name:",block_name,
                        "block_seg:", to_json(block_seg),
                        )

            # if check_type(block_seg) != "DICT":
            #    if DBUG:
            #        do_DBUG("((((((((((((((((((",
            #                "check_type:",
            #                check_type(block_seg),
            #                "["+block_name+"]:",
            #                block_seg[0],
            #                "))))))))))))))))))")

            if check_type(block_seg) == "LIST":
                if DBUG:
                    do_DBUG("LIST returned",
                            block_seg)
                if not block_seg == []:
                    out_dict[block_name] = block_seg[0]
            else:
                if DBUG:
                    do_DBUG("Not List",
                            block_seg)
                out_dict[block_name] = block_seg


            if DBUG:
                do_DBUG("out_dict["+ block_name + "]:", to_json(out_dict))

            # if (i + 1) <= (len(ln_list) - 1):
                # We are not passed the end of the list
                # so increment the i counter in the call to
                # process_segment

            #    i, sub_seg, seg_name = process_segment(i + 1, ln_ctrl,
            #                                           match_ln,
            #                                           ln["level"],
            #                                           ln_list)

            if DBUG:
                do_DBUG("============================",
                        "seg_name:", seg_name,
                        "segment returned:", sub_seg,
                        "Returned with counter-i:", i,
                        "----------------------------",
                        "out_dict[" + seg_name + "]",
                        to_json(out_dict[seg_name]),
                        "block_name:", block_name,
                        "block_seg:", block_seg)

        if DBUG:
            do_DBUG("====================END of LOOP",
                    "line number(i):", i,
                    "out_dict", to_json(out_dict),
                    "===============================")

        # increment line counter
        i += 1

    if DBUG:
        do_DBUG("End of list:", i,
                "out_dict", to_json(out_dict))

    return out_dict

def cms_file_parse2(inPath):
    # Parse a CMS BlueButton file (inPath)

    result = cms_file_read(inPath)

    # Set default variables on entry
    k = ""
    v = ""
    items = collections.OrderedDict()

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
                    # if multi:
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
                if not divider in l:
                    if len(l.strip()) > 0:
                        # print "title length:", len(l.strip())

                        # Remove : from Title - for Claims LineNumber:
                        titleline = l.split(":")
                        tl = titleline[0].rstrip()

                        previous_segment = current_segment
                        header_block = get_segment(headlessCamel(tl))
                        # print headlessCamel(l), "translated:",
                        # header_block

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
                        # print i, "got date for:",
                        # current_segment, k, ":", v

                        segment_dict[k] = v

                    elif k.upper() == "SOURCE":
                        segment_source=set_source(segment_source, k, v)
                        # Apply headlessCamelCase to K
                        k = headlessCamel(k)
                        v = segment_source
                        # print i, "set source in:",
                        # current_segment, ":", k, ":", v

                        segment_dict[k] = v

                    else:
                        # match key against segment
                        match_string = current_segment + "." + k

                        print "Match:", match_string

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
                            if k in segment_dict:
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
    items, segment_dict, line_list = write_segment(items,
                                                   current_segment,
                                                   segment_dict,
                                                   line_list,
                                                   multi)

    return items


def cms_file_parse(inPath):
    # Parse a CMS BlueButton file (inPath)
    # Using a redefined Parsing process

    # Set default variables on entry
    k = ""
    v = ""
    items = collections.OrderedDict()
    first_header = True
    header_line = True
    get_title = False

    line_type = "Header"
    segment_dict = collections.OrderedDict()
    current_segment = ""
    segment_source = ""
    previous_segment = current_segment
    line_dict = collections.OrderedDict()

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

            if len(l) <= 1 and header_line is False:
                # The line is a detail line and is empty
                # so ignore it and move on to next line
                # print "empty line %s[%s] - skipping to next line" % (i,l)
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
                header_line = True
                get_title = True
                # First we need to write the old segment out
                if first_header:
                    # file starts with a header line but
                    # there is nothing to write
                    first_header = False
                    # print "First Header - Nothing to write"
                    continue
                else:
                    # not the first header so we should write the segment
                    # print "Not First Header - Write segment"
                    print i, "writing segment",
                    items, segment_dict = write_segment(items,
                                                        current_segment,
                                                        segment_dict)
                    # Then we can continue
                    continue

            #print "HL/GT:",header_line,get_title
            if header_line and get_title:
                if not divider in l:
                    previous_segment = current_segment
                    # assign title to current_segment
                    current_segment = k.lower().replace(" ", "_")
                    get_title = False

                else:
                    # blank lines for title were skipped so we hit divider
                    # before setting current_segment = title
                    # So set to "claim_summary"
                    # since this is only unnamed segment
                    current_segment = "claim_summary"
                    get_title = False

                # print "Header:",current_segment
                # now match the title in seg["key"]
                # and write any prefill information to the segment
                if find_segment(k):
                    # Check the seq list for a match
                    # print "Segment list: %s FOUND" % l
                    seg_returned = get_segment(k)
                    k = seg_returned["name"]
                    # print "k set to [%s]" % k

                    current_segment, segment_dict = segment_prefill(seg_returned)

                    # print "segment_dict: %s" % segment_dict
                else:
                    # We didn't find a match so let's set it to "Other"
                    current_segment = k.lower().replace(" ", "_")
                    segment_dict = collections.OrderedDict()
                    segment_dict[current_segment] = {}

                print "%s:Current_Segment: %s" % (i, current_segment)
                # print "Header Line:",header_line
                # go to next line in file
                continue

            print "[%s:CSeg:%s|%s L:[%s]" % (i,current_segment,line_type,l)

            # print "%s:Not a Heading Line" % i
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
                    segment_dict[current_segment] = {k: v}
                    continue
            segment_source = set_source(segment_source, k, v)
            if k.upper() == "SOURCE":
                k = k.lower()
                v = segment_source
                segment_dict[current_segment] = {k: v}
                continue

            line_dict[k] = v

            # print "line_dict:", current_segment,":", line_dict

            segment_dict[current_segment] = line_dict

            # reset the line_dict
            line_dict = collections.OrderedDict()

        # end of for loop

    f.close()
    # write the last segment
    # print "Writing the last segment"
    items, segment_dict = write_segment(items,
                                        current_segment,
                                        segment_dict)

    return items


def set_header_line(hl):
    # flip header_line value. received as hl (True or False)

        return (not hl)


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

    return mk


def get_header_block_level(header_block):

    lvl = 0
    if "level" in header_block:
        lvl = header_block["level"]

    return lvl

