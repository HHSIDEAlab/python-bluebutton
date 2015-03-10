"""
python-bluebutton
FILE: cms_parser_utilities
Created: 3/9/15 5:34 PM


"""
__author__ = 'Mark Scrimshire:@ekivemark'

from datetime import datetime, date, timedelta


import collections

from file_def_cms import SEG_DEF

def process_segment(strt_ln, ln_control, match_ln, start_lvl, ln_list):
    # Process a segment of the list while level is
    # greater than current level or undefined

    # Input:
    # start_ln = current line in the dict
    # ln_control = entry from SEG_DEF for the start_ln
    # match_ln = array to build a breadcrumb match setting
    # eg. emergencyContact.name.address
    # start_lvl = current level for record. top level = 0
    # ln_list = the dict of lines to process
    # { "0": {
    #        "line": "MYMEDICARE.GOV PERSONAL HEALTH INFORMATION",
    #        "type": "HEADER",
    #        "key": 0,
    #        "level": 0
    #    }
    # },

    # Every entry in ln_list has a level assignment

    # Step 1 is to setup the segment using the start_ln record

    current_source = ""
    work_ln = strt_ln
    multi = False
    segment = collections.OrderedDict()
    segment_list = []
    sub_segment = collections.OrderedDict()
    list_processing = False
    dict_in_list = False

    # print "Line_Control:Pre List eval", ln_control

    if key_is_in("type", ln_control):
        # initialize segment variable
        if ln_control["type"] == "string":
            segment = ""
            list_processing = False
            dict_in_list = False

        elif ln_control["type"] == "list":
            # print "WE HAVE A LIST TO DEAL WITH"
            segment_list = []
            if key_is_in("sub_type", ln_control):
                if ln_control["sub_type"] == "dict":
                    dict_in_list = True
                    sub_segment = collections.OrderedDict()

                else:
                    dict_in_list = False
                    sub_segment = ""
            list_processing = True
            # print "Dict in List: ", dict_in_list

        else:
            segment = collections.OrderedDict()
            list_processing = False
            dict_in_list = False

    else:
        segment = collections.OrderedDict()
        list_processing = False

    multi = is_multi(ln_control)
    # Determine if multiple sub-entries might be found

    if key_is_in("name", ln_control):
        current_segment = ln_control["name"]
    else:
        current_segment = "otherSegment" + str(work_ln)

    if key_is_in("pre", ln_control):
        assigned_segment, segment = segment_prefill(ln_control)
        # print "Segment:", segment
        # print "Current Seg:", current_segment
    else:
        segment= collections.OrderedDict()

    if key_is_in("level", ln_control):
        match_ln = update_match(ln_control["level"], current_segment, match_ln)

    # Now loop through the lines in the file
    # until we match another SEG_DEF record

    end_segment = False

    k = ""
    v = ""

    current_line =get_line_dict(ln_list, work_ln)

    if not is_body(current_line):
        # If we are dealing with a header we have already processed it
        # so move to next line
        # print "HEADER"
        work_ln += 1


    while not end_segment and (work_ln <= len(ln_list)-1):
        if work_ln == (len(ln_list)-1):
            # We have reached the end of the list
            end_segment = True


        # Get the line to work with
        current_line = get_line_dict(ln_list, work_ln)

        #print "==========="
        #print "current_line:", current_line
        #print "==========="
        ttl, val = split_k_v(current_line["line"])
        match_ln = update_match(current_line["level"], ttl, match_ln )
        # print "matching with: ",match_ln

        adj_level = adjusted_level(current_line["level"],match_ln)
        # print "Adjusted_Level:",adj_level
        if adj_level <= start_lvl:
            # We have found the start of the next segment
            # print "onto next segment"

            end_ln = work_ln - 1
            end_segment = True
        elif adj_level == (start_lvl + 1):
            # We are processing the lines in the segment

            print "Process Current Line:", current_line
            # we need to check SEG_DEF for instructions
            match_ln = update_match(start_lvl + 1, headlessCamel(current_line["line"]), match_ln)
            # print "combined match:", combined_match(start_lvl + 1, match_ln)

            if find_segment(combined_match(start_lvl + 1, match_ln)):
                sub_seg = get_segment(combined_match(start_lvl + 1, match_ln))
                print "entering sub process segment"
                work_ln, sub_seg, seg_name = process_segment(work_ln, sub_seg, match_ln, start_lvl + 1, ln_list)
                work_ln += 1
                segment[seg_name] = sub_seg

            if find_segment(combined_match(start_lvl + 1, match_ln)):
                # we found a combined item that
                # must be drilling down another level
                # work_ln, segment = process_segment(work_ln,
                # get_segment(combined_match(ln_control["level"] + 1, match_ln),
                #                    match_ln, ln_control["level"], ln_list)
                print ">>>>>>>>>>>>>"
                print "ln:", work_ln, "Going Deeper:", \
                    combined_match(ln_control["level"] + 1, match_ln)

                block_control = get_segment(combined_match(start_lvl + 1, match_ln))
                work_ln, sub_seg, seg_name = process_segment(work_ln, block_control, match_ln, start_lvl + 1, ln_list)
                work_ln += 1
                segment[seg_name] = sub_seg



            else:
                line_source = current_line["line"].split(":")

                if len(line_source) > 1:
                    k = headlessCamel(line_source[0])
                    v = line_source[1].lstrip()
                    v = v.rstrip()
                else:
                    k = "comments"
                    v = current_line["line"]

                if "SOURCE" in k.upper():
                    k = headlessCamel(k)
                    v = set_source(current_source,k,v)
                    current_source = v
                    print "SET source:",current_source

                if (k[2] == "/") and (ln_control["name"] == "header"):
                    # print "got the date line in the header"
                    v = {"value": parse_time(current_line["line"])}
                    k = "effectiveTime"
                    # segment[current_segment]={k: v}

                if "DATE" in k.upper():
                    v = parse_date(v)
                if "DOB" == k.upper():
                    v = parse_date(v)
                if "DOD" == k.upper():
                    v = parse_date(v)

                if ("ADDRESSLINE1" in k.upper()) or ("ADDRESSTYPE" in k.upper()):
                    v, work_ln = build_address(ln_list, work_ln)
                    # print "work_ln = ", work_ln
                    k = "address"

                    # Build an Address Block
                    # By reading the next lines
                    # until we find "ZIP"
                    #return Address dict and work_ln reached

                if list_processing:
                    if dict_in_list:
                        if k in sub_segment:
                            # this entry exists
                            # so post the current information
                            # reset the segment_list
                            # and append the latest data to a new subset
                            segment_list.append(sub_segment)
                            sub_segment = collections.OrderedDict()
                            sub_segment["source"] = current_source

                        sub_segment[k] = v
                    else:
                        segment_list.append({k: v})
                        if not "source" in segment_list:
                            # print "SETTING source in segment list:", current_source
                            segment_list.append({"source": current_source})
                        else:
                            segment_list.append(v)
                else:
                    segment[k] = v
                    if not "source" in segment:
                        # print "SETTING source in segment:", current_source

                        segment["source"] = current_source


        elif adj_level >= (start_lvl + 2):
            # level >= start_level + 2
            # we are going down another level
            seg_def = get_segment(combined_match(start_lvl + 1, match_ln))
            # print "Deal as Sub-segment:"
            # print "process ", current_line["line"]
            # print "seg_def:", seg_def
            work_ln, sub_segment, segment_name = process_segment(work_ln, seg_def, match_ln, start_lvl + 1, ln_list)
            # print "SubSegment:", sub_segment
            segment[segment_name]= sub_segment
            # print "current_segment:", segment[segment_name]
            work_ln += 1

    # If match on SEG_DEF and level is > current level
    # Drill down to another sub-segment


    # else: we have found the start of the next segment
    # So set return values and exit

        work_ln += 1

    # finish writing segments
    if list_processing:
        #segment[current_segment] = sub_segment
        # print "segment_list before exit:", segment_list
        # print "segment before exit:", segment
        segment = segment_list

        # print "updated segment", segment
        # print "Cur Seg Name:", current_segment
    end_ln = work_ln-2

    return end_ln, segment, current_segment



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

def get_segment(title):

    result = {}

    # cycle through the seg dictionary to match against title
    for ky in SEG_DEF:
        # print "ky", ky, "Title:", title, "Match:", ky["match"]
        if title in ky["match"]:
            result = ky
            break

    return result

def find_segment(title):

    result = False
    for ky in SEG_DEF:
        # print k
        if title in ky["match"]:
            # print "Match: %s : %s" % (title, ky['key'])
            result = True
            break

    return result

def combined_match(lvl, match_ln):

    ctr = 0
    combined_header = ""
    # print match_ln
    while ctr <= lvl:
        if ctr == 0:
            combined_header = match_ln[ctr]
        else:
            combined_header = combined_header + "." + match_ln[ctr]

        ctr += 1

    return combined_header

def update_match(lvl, txt, match_ln):
    # Update the match_ln list

    line = txt.split(":")
    if len(line) >1:
        k = line[0]
    else:
        k = txt

    match_ln[lvl] = k

    return match_ln


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
        # print "Multi List:", ln_list
        itm[sgmnt] = ln_list
    else:
        itm[sgmnt] = sgmnt_dict

    return itm, sgmnt_dict, ln_list


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

def parse_time(t):
    # convert time to  json format
    t = t.strip()
    time_value = datetime.strptime(t, "%m/%d/%Y %I:%M %p")
    # print time_value
    return_value = time_value.strftime("%Y%m%d%H%M%S+0500")

    # print return_value
    return return_value

def parse_date(d):
    # convert date to json format
    return_value = ""
    d = d.strip()
    if len(d) > 0:
        print d
        date_value = datetime.strptime(d, "%m/%d/%Y")
        return_value = date_value.strftime("%Y%m%d")

    #print return_value
    return return_value

def set_source(current_source, key, value):
    # Set the source of the data

    result = current_source
    if key.upper() == "SOURCE":
        # print "Found Source: [%s:%s]" % (key,value)
        if value.upper() == "SELF-ENTERED":
            result = "patient"
        elif value.upper() == "MYMEDICARE.GOV":
            result = "MyMedicare.gov"
        else:
            result = value.upper()
        # print "[%s]" % result

    return result

def key_is_in(ky,dt):
    # Check if key is in dict
    result = False
    if ky in dt:
        result = True

    return result

def is_multi(ln_dict):
    # Check value of "Multi" in ln_dict
    result = False
    if key_is_in("multi", ln_dict):
        mult = ln_dict["multi"].upper()
        if mult == "TRUE":
            result = True
    else:
        result = False

    return result

def get_line_dict(ln, i):
    # Get the inner line dict from ln

    found_line = ln[i]
    extract_line = found_line[i]

    return extract_line

def is_body(ln):
    # Is line type = "BODY"

    result = False
    if key_is_in("type", ln):
        if ln["type"].upper() == "BODY":
            result = True

    return result


def split_k_v(l):
    # split out line in to k and v split on ":"

    line_source = l.split(":")
    if len(line_source) > 1:
        k = headlessCamel(line_source[0])
        v = line_source[1].lstrip()
        v = v.rstrip()
    else:
        k = "comments"
        v = l
    return k,v


def build_address(ln_list, wk_ln):
    # Build address block
    # triggered because current line has
    # k.upper() == "ADDRESSLINE1" or "ADDRESSTYPE"
    # so read until k.upper() == "ZIP"
    # then return address block and work_ln reached

    address_block = collections.OrderedDict([("addressType", ""),
                    ("addressLine1", ""),
                    ("addressLine2", ""),
                    ("city", ""),
                    ("state", ""),
                    ("zip", "")
                     ])

    end_block = False
    while not end_block:

        ln_dict = get_line_dict(ln_list, wk_ln)
        l = ln_dict["line"]

        k, v = split_k_v(l)
        # print wk_ln, ":", k

        if k in address_block:
            address_block[k] = v
            end_block = False
            wk_ln += 1
        else:
            end_block = True


    return address_block, wk_ln - 1

def adjusted_level(lvl, match_ln):
    # lookup the level based on the max of source line lvel
    # and SEG_DEF matched level

    result = lvl
    if find_segment(combined_match(lvl,match_ln)):
        seg_info = get_segment(combined_match(lvl, match_ln))
        if key_is_in("level", seg_info):
            result = max(lvl, seg_info["level"])
    else:
        result = lvl

    # print "match result", result , "(", lvl, ")"
    return result



