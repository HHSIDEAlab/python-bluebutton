"""
python-bluebutton
FILE: cms_parser_utilities
Created: 3/9/15 5:34 PM

Takes CMS BlueButton v2.0 File and converts to JSON
This provides partial compatibility with full JSON/XML format

"""
__author__ = 'Mark Scrimshire:@ekivemark'

from datetime import datetime, date, timedelta

import json
import collections
import inspect
import six

from file_def_cms import SEG_DEF
from usa_states import STATES

def process_header(strt_ln, ln_control, strt_lvl, ln_list):
    # Input:
    # strt_ln = current line number in the dict
    # ln_control = entry from SEG_DEF for the start_ln
    # match_ln = list array to build a breadcrumb match setting
    # eg. emergencyContact.name.address
    # start_lvl = current level for record. top level = 0
    # ln_list = the dict of lines to process
    # { "0": {
    # "line": "MYMEDICARE.GOV PERSONAL HEALTH INFORMATION",
    #        "type": "HEADER",
    #        "key": 0,
    #        "level": 0
    #    }
    # },

    DBUG = False

    wrk_add_dict = collections.OrderedDict()

    # Setup
    # we dropped in to this function because we found a SEG_DEF dict
    # which was loaded in to ln_control.

    segment = ln_control["name"]

    wrk_ln_dict = get_line_dict(ln_list, strt_ln)
    # Load wrk_ln_dict ready for evaluating line in setup_header

    wrk_add_dict = setup_header(ln_control, wrk_ln_dict)
    # ln_ctrl = SEG_DEF entry
    # wrk_ln_dict is the current line from ln_list[strt_ln]

    return strt_ln, wrk_add_dict, segment


def process_subseg(strt_ln, ln_control, match_ln, strt_lvl,
                   ln_list, seg, seg_name):
    # Input:
    # strt_ln = current line number in the dict
    # ln_control = entry from SEG_DEF for the start_ln
    # match_ln = list array to build a breadcrumb match setting
    # eg. emergencyContact.name.address
    # start_lvl = current level for record. top level = 0
    # ln_list = the dict of lines to process
    # { "0": {
    # "line": "MYMEDICARE.GOV PERSONAL HEALTH INFORMATION",
    #        "type": "HEADER",
    #        "key": 0,
    #        "level": 0
    #    }
    # },
    # seg = dict returned from process_header
    # seg_name = dict key in seg returned from process_header

    # FIXED: email address not written in patient section
    # FIXED: Write phones as dict in patient section
    # FIXED: medicalConditions - 2nd items is skipped
    # FIXED: Double comment lines written in allergies sections
    # FIXED: Allergies section is empty
    # FIXED: Medications - last entry does not get source info

    # FIXED: Fix Funky errors [Family History] - some entries not written
    # FIXED: Preventive Services - Some items not added
    # FIXED: Providers - last entry does not get source info
    # FIXED: Providers - Fields not in order
    # FIXED: Pharmacies - Last record missing Pharmacy Name
    # FIXED: Pharmacies - last entry does not get source info
    # FIXED: missing "category": "Medicare" fixed with "Pre" definition

    # FIXED: category dict written after insurance section
    # FIXED: Employer Subsidy Header not written
    # FIXED: Primary Insurance Header not written
    # FIXED: Other Insurance Header not written

    # FIXED: Claim Details need to be embedded inside Claim Header
    # FIXED: Write Claim details as list of dicts with new dict on repeat of
    #       line number
    # FIXED: Multiple Claims Headers and Details not handled
    # FIXED: Claims - First Header and Last Claim Detail written
    # FIXED: Fix Time fields (minutes dropped after colon)

    # FIXED: Last Claim Header is appended to previous claim line
    # FIXED: Last Claim number section does not get sub-listed inside
    # claim header section (probably due to bug in claim header)

    # FIXED: comments in header are dropped. Change Assign_key_value()
    # FIXED: Time in header is not written
    # FIXED: Removed "/" from field names (kvs["k"]) in
    #        assign_key_values()

    # The claims section of the CMS BlueButton file appears to have an
    # issue. The Claim Headers are not titled there is only the to
    # dashed lines BUT the last claim header does not get preceded by
    # the dashed lines. So there is nothing to indicate a new claim.
    #
    # Therefore implement a fix that since the claims come at the end
    # of the file we will assign a claim number field in to the line dict
    # we create and increment that on change of "Line Number" found in
    # the lines

    DBUG = False

    current_segment = seg_name
    seg_type = check_type(seg[seg_name])
    end_segment = False
    wrk_ln = strt_ln

    wrk_seg_def = {}

    ln_control_alt = ln_control

    wrk_ln_head = False
    kvs = {"k": "", "v": "", "source": "", "comments": [], "ln": 0}
    wrk_segment = seg_name
    multi = key_is("multi", ln_control, "TRUE")

    # save_to = seg[seg_name]
    # Disable pre-writing of save_to and add to process_dict instead
    save_to = {}

    if DBUG:
        do_DBUG("pre-load data passed to " + seg_type + " <<<<<<<<<<<<<<<",
                "seg[" + seg_name + "]:",
                to_json(seg[seg_name]))

    process_dict = collections.OrderedDict(seg[seg_name])
    process_list = []

    # get current line
    current_line = get_line_dict(ln_list, wrk_ln)
    wrk_ln_lvl = current_line["level"]

    # Update match_ln with headers name from SEG_DEF (ie. ln_control)
    match_ln = update_match(strt_lvl, seg_name, match_ln)

    match_hdr = combined_match(wrk_ln_lvl, match_ln)
    # Find segment using combined header

    if DBUG:
        do_DBUG(">>==>>==>>==>>==>>==>>==>>==>>==>>==>>==>>",
                "type:", seg_type,
                "seg", to_json(seg),
                "seg_name:", seg_name,
                "ln_control:", to_json(ln_control),
                "strt_lvl:", strt_lvl,
                "match_ln:", match_ln,
                ">>==>>==>>==>>==>>==>>==>>==>>==>>==>>==>>")

    while not end_segment and (wrk_ln <= len(ln_list) - 1):
        if wrk_ln == len(ln_list) - 1:
            end_segment = True

        # not at end of file

        if DBUG:
            do_DBUG(">>>>>TOP of while loop",
                    "wrk_ln:", wrk_ln,
                    "current_line:", to_json(current_line),
                    "match_ln:", match_ln,
                    "process_dict:", to_json(process_dict),
                    "process_list:", process_list)

        # update the match string in match_ln

        is_line_seg_def = find_segment(match_hdr, True)
        # Find SEG_DEF with match exact = True

        if DBUG:
            do_DBUG("*****************PRESET for line***********",
                    "wrk_ln_lvl:", wrk_ln_lvl,
                    "match_ln:", match_ln,
                    "match_hdr:", match_hdr,
                    "is_line_seg_def:", is_line_seg_def,
                    "wrk_seg_def:", wrk_seg_def)

        if is_line_seg_def:
            # We found an entry in SEG_DEF using match_hdr

            wrk_seg_def = get_segment(match_hdr, True)
            # We found a SEG_DEF match with exact=True so Get the SEG_DEF

            match_ln = update_match(wrk_ln_lvl, wrk_seg_def["name"],
                                    match_ln)
            # update the name in the match_ln dict

            # we also need to check the lvl assigned to the line from
            # SEG_DEF
            wrk_ln_lvl = wrk_seg_def["level"]
            multi = key_is("multi", wrk_seg_def, "TRUE")

            if DBUG: # or True:
                do_DBUG("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                        "is_line_seg_def:", is_line_seg_def,
                        "wrk-seg_def:", to_json(wrk_seg_def),
                        "match_ln:", match_ln,
                        "wrk_ln:", wrk_ln,
                        "strt_ln:", strt_ln,
                        "current_line type:", current_line["type"])

            if (wrk_ln != strt_ln) and (is_head(current_line)):
                # we found a new header
                # We have to deal with claims lines and claims headers
                # within claims. They have a different level value
                # So test for level = strt_lvl
                if DBUG:
                    do_DBUG("DEALING WITH NEW HEADER:",
                            current_line["line"])

                # set wrk_ln_head = True
                wrk_ln_head = True
                wrk_ln_lvl = get_level(wrk_seg_def)

                if DBUG: # or True:
                    do_DBUG("RECURSIVE CALL",
                            "wrk_ln:", wrk_ln,
                            "wrk_seg_def:", wrk_seg_def,
                            "match_ln:", match_ln,
                            "wrk_ln_lvl:", wrk_ln_lvl,
                            "process_list:", process_list,
                            "process_dict:", process_dict,
                            "seg:", seg,
                            "seg_name:", seg_name)

        else:
            # NOT is-line-seg_def
            if DBUG: # or True:
                do_DBUG("--------------------------------",
                        "wrk_ln:", wrk_ln,
                        "wrk_ln_head:", wrk_ln_head,
                        "wrk_seg_def:", wrk_seg_def,
                        "updating wrk_seg_def",
                        "ln_control_alt:", ln_control_alt,
                        "SETTING to ln_control_alt")
            if not ln_control_alt == {}:
                wrk_seg_def = ln_control_alt
            else:
                wrk_seg_def = ln_control

        # Get key and value
        kvs = assign_key_value(current_line,
                               wrk_seg_def,
                               kvs)

        if DBUG:
            do_DBUG("wrk_ln_lvl:", wrk_ln_lvl, "match_hdr:", match_hdr,
                    "kvs:", kvs,
                    "Multi:", multi,
                    "is_line_seg_def:", is_line_seg_def,
                    "process_dict:", to_json(process_dict),
                    "process_list:", process_list,
                    "end_segment:", end_segment,
                    "wrk_ln_head:", wrk_ln_head)

        # Update kvs to dict or list
        if not end_segment:
            # We need to process the line

            # assign "pre" values from SEG_DEF
            # to work_add_dict
            if DBUG:
                do_DBUG("WRK_LN_HEAD:", wrk_ln_head,
                        "wrk_seg_def:", wrk_seg_def,
                        "process_dict:", process_dict,
                        "process_list:", process_list)

            if wrk_ln_head:
                # Post the dict to a list and clear down
                # before writing pre-fill
                # check for source and write it to process_dict

                # Move to sub-function()

                process_dict, process_list, = write_proc_dl(kvs,
                                                            process_dict,
                                                            process_list)

                # Replace code with sub-function()

                # Now clear down the dict and
                # add the new item

                process_dict = collections.OrderedDict()

                wrk_segment, process_dict = segment_prefill(wrk_seg_def,
                                                            process_dict)

                if DBUG:
                    do_DBUG("Just ran segment_pre-fill:", wrk_ln_head,
                            "wrk_segment:", wrk_segment,
                            "process_dict:", to_json(process_dict),
                            "process_list:", process_list)

            else:  # NOT wrk_ln_head
                if DBUG: # or True:
                    do_DBUG("wrk_ln_head:", wrk_ln_head,
                            "process_dict:", process_dict,
                            "PROCESS_LIST:", process_list)

            # Do we need to override the key using field or name
            # from SEG_DEF?

            # pass in match_ln, match_hdr, and wrk_lvl to allow
            # Override to be checked

            if "SOURCE" in kvs["k"].upper():
                # source was saved in the assign step.
                # we don't write it out now. instead save it till a block
                # is written
                pass

            # Now we check if we are dealing with an address block
            if ("ADDRESSLINE1" in kvs["k"].upper()) or \
                    ("ADDRESSTYPE" in kvs["k"].upper()):
                # Build an Address Block
                # By reading the next lines
                # until we find "ZIP"
                # return Address dict and work_ln reached

                kvs["v"], wrk_ln = build_address(ln_list, wrk_ln)
                kvs["k"] = "address"
                if DBUG:
                    do_DBUG("Built Address wrk_ln now:", wrk_ln,
                            "k:", kvs["k"], "v:", kvs["v"])

            if "COMMENTS" in kvs["k"].upper() and not wrk_ln_head:
                # print "We found a comment", kvs["k"],":", kvs["v"]
                # and we are NOT dealing with a header
                # if value is assigned to comments we need to check
                # if comments already present
                # if so, add to the list

                process_dict = write_comment(process_dict, kvs)

                if DBUG:
                    do_DBUG("is_line_seg_def:", is_line_seg_def,
                            "wrk_seg_def", wrk_seg_def,
                            "wrk_ln:", wrk_ln,
                            "kvs:", kvs,
                            "current_line:", current_line,
                            "process_dict:", process_dict)

            if multi:
                if DBUG:
                    do_DBUG("******************************",
                            "MULTI:", multi)
                if key_is("type", wrk_seg_def, "LIST"):
                    if key_is("sub_type", wrk_seg_def, "DICT"):
                        if DBUG:
                            do_DBUG("LIST and sub_type: DICT",
                                    "process_dict:", process_dict,
                                    "process_list:", process_list,
                                    "kvs:", kvs)
                        if kvs["k"] in process_dict:
                            if DBUG:
                                do_DBUG("k:",
                                        kvs["k"], "in: ",
                                        process_dict)

                            process_dict, process_list = write_proc_dl(kvs, process_dict, process_list)
                            # Now clear down the dict and
                            # add the new item

                            process_dict = collections.OrderedDict()

                            if not kvs["k"].upper() == "COMMENTS":
                                # print "skipping comments"
                                process_dict[kvs["k"]] = kvs["v"]
                            # print "process_dict (after write):", \
                            #    process_dict
                        else:
                            process_dict[kvs["k"]] = kvs["v"]
                            if DBUG: # or True:
                                do_DBUG("After " + kvs["k"] + " not found",
                                        "in process_dict:", process_dict,
                                        "SO IT WAS ADDED")
                    else:
                        if key_is_in("sub_type", wrk_seg_def):
                            if DBUG: # or True:
                                do_DBUG("wrk_seg_def sub_type:",
                                        wrk_seg_def["sub_type"])

                        process_dict[kvs["k"]] = [kvs["v"]]
                        # print "process_dict:", process_dict
                        # TESTING disabling save_to write
                        # save_to = write_save_to(save_to, process_dict)

                elif key_is("type", wrk_seg_def, "DICT"):
                    # print "wrk-seg_def:", wrk_seg_def
                    if key_is("sub_type", wrk_seg_def, "DICT"):
                        if DBUG: # or True:
                            do_DBUG("DICT and sub_type: DICT",
                                    "write " + wrk_seg_def["name"] + ":",
                                    kvs["v"],
                                    "ln_control:", to_json(ln_control),
                                    "wrk_seg_def:", to_json(wrk_seg_def),
                                    "current_line:", to_json(current_line),
                                    "process_dict:", to_json(process_dict),
                                    "process_list:", process_list,
                                    "kvs:", kvs)

                        # Write what
                        if not kvs["k"].upper() == "SOURCE":
                            # process_dict[wrk_seg_def["name"]] = kvs["v"]
                            process_dict[kvs["k"]] = kvs["v"]
                        if DBUG:
                            do_DBUG("just wrote non-source line",
                                    "process_dict:", process_dict)

                    else:
                        if DBUG:
                            do_DBUG("No sub_type")
                        if key_is_in("sub_type", wrk_seg_def):
                            if DBUG:
                                do_DBUG("type: DICT and sub_type:",
                                        wrk_seg_def["sub_type"])
                        else:
                            if DBUG:
                                do_DBUG("writing to process_dict:",
                                        process_dict)

                            # type: dict
                            # dict_name: phone
                            # field : home
                            # k: homePhone v = ""
                            # needs to get written as
                            # phone {"home": "", "work": "", "mobile": ""}
                            # process_dict[wrk_seg_def["dict_name"]] =
                            #               {wrk_seg_def["field"]: kvs["v"]
                            # follow on elements need to check:
                            # wrk_seg_def["dict_name"] or kvs["k"]

                            if key_is_in_subdict(kvs["k"], process_dict):
                                # write the source first
                                if DBUG:
                                    do_DBUG("roll a new process_dict")
                                process_dict = write_source(kvs,
                                                            process_dict)
                                # Append to the list
                                process_list.append(process_dict)
                                # Now clear down the dict and
                                # add the new item
                                process_dict = collections.OrderedDict()
                                process_dict[kvs["k"]] = kvs["v"]

                            if DBUG:
                                do_DBUG("didn't find:", kvs["k"],
                                        "is_line_seg_def:",
                                        is_line_seg_def)

                            if is_line_seg_def and key_is_in("dict_name",
                                                             wrk_seg_def):
                                if DBUG:
                                    do_DBUG("got dict_name:",
                                            wrk_seg_def["dict_name"])
                                if not key_is_in(wrk_seg_def["dict_name"],
                                                 process_dict):
                                    if DBUG:
                                        do_DBUG("no dict_name")

                                    process_dict[wrk_seg_def["dict_name"]] = {wrk_seg_def["name"]: kvs["v"]}
                                    # process_dict[kvs["k"]] = kvs["v"]
                                else:
                                    if DBUG:
                                        do_DBUG("&&&&&&&&&&&&&&&&&&&&&&&&",
                                                "updating process_dict:",
                                                process_dict,
                                                "&&&&&&&&&&&&&&&&&&&&&&&&",
                                                "with kvs:", kvs)
                                    # process_dict[wrk_seg_def
                                    # ["dict_name"]] =kvs["v"]
                                    if check_type(process_dict[wrk_seg_def["dict_name"]]) == "DICT":
                                        process_dict[wrk_seg_def["dict_name"]].update({wrk_seg_def["name"]: kvs["v"]})
                                    else:
                                        process_dict[wrk_seg_def["dict_name"]] = kvs["v"]
                            else:
                                if DBUG:
                                    do_DBUG("didn't get dict_name:", kvs)
                                # process_dict[kvs["k"]] = kvs["v"]

                                ### TESTING disabling SAVE_TO
                                # save_to[kvs["k"]] = kvs["v"]
                                process_dict.update({kvs["k"]: kvs["v"]})
                                if DBUG:
                                    do_DBUG("process_dict updated to:",
                                            process_dict)

                else:
                    if key_is_in("type", wrk_seg_def):
                        if DBUG:
                            do_DBUG("wrk-seg_def - Type is:",
                                    wrk_seg_def["type"],
                                    "KVS:", kvs)

            else:  # not multi
                if key_is("type", wrk_seg_def, "DICT"):

                    if DBUG:
                        do_DBUG("Multi:", multi, " and type: DICT")

                    if kvs["k"].upper() == "COMMENTS" and \
                            key_is_in("comments",
                                      process_dict):
                        pass
                    else:
                        if not is_line_seg_def:
                            # We have no special processing rules for
                            # this line
                            if DBUG:
                                do_DBUG("is_line_seg_def:",
                                        is_line_seg_def,
                                        "kvs:", kvs)
                            process_dict[kvs["k"]] = kvs[ "v"]
                            # save_to[kvs["k"]] = kvs["v"]

                        elif key_is_in("dict_name", wrk_seg_def):
                            if DBUG:
                                do_DBUG("processing:",
                                        wrk_seg_def["dict_name"],
                                        "kvs:", kvs,
                                        "process_dict:", process_dict)
                            if key_is_in(wrk_seg_def["dict_name"],
                                         process_dict):
                                process_dict[
                                    wrk_seg_def["dict_name"]].update(
                                    {kvs["k"]: kvs["v"]})
                            else:
                                if DBUG:
                                    do_DBUG("wrk_seg_def:", wrk_seg_def,
                                            "kvs:", kvs)
                                process_dict[wrk_seg_def["dict_name"]] = \
                                    collections.OrderedDict(
                                        {kvs["k"]: kvs["v"]})
                        else:
                            process_dict[kvs["k"]] = kvs["v"]

                elif key_is("type", wrk_seg_def, "LIST"):
                    if DBUG:
                        do_DBUG("Multi:", multi,
                                " and type: LIST",
                                "process_dict:", to_json(process_dict))
                    process_dict = update_save_to(process_dict, kvs,
                                                  kvs["k"], "v")
                    # save_to.extend([kvs["k"],kvs["v"]])

                if DBUG:
                    do_DBUG("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",
                            "WHAT GETS WRITTEN HERE?",
                            "MULTI:", multi,
                            "kvs:", kvs,
                            "ln_control:", to_json(ln_control),
                            "wrk_seg_def:", to_json(wrk_seg_def),
                            "current_line:", to_json(current_line),
                            "process_dict:", to_json(process_dict),
                            "process_list:", process_list,
                            "save_to:", to_json(save_to))

        wrk_ln_head = False
        # reset the Header indicator
        wrk_ln += 1
        # increment the line counter
        if wrk_ln < len(ln_list) - 1:
            current_line = get_line_dict(ln_list, wrk_ln)
            wrk_ln_lvl = current_line["level"]
            # update the match string in match_ln
            if find_segment(headlessCamel(current_line["line"]),
                            exact=True):
                wrk_seg_def = get_segment(
                    headlessCamel(current_line["line"]), exact=True)
                wrk_ln_lvl = max(current_line["level"],
                                 wrk_seg_def["level"])

            match_ln = update_match(wrk_ln_lvl,
                                    headlessCamel(current_line["line"]),
                                    match_ln)
            match_hdr = combined_match(wrk_ln_lvl, match_ln)
            # Find segment using combined header
            wrk_seg_def = get_segment(match_hdr, True)
            if is_head(current_line):
                ln_control_alt = wrk_seg_def
            # We found a SEG_DEF match with exact=True so Get the SEG_DEF

            if is_head(current_line) and (wrk_ln_lvl == strt_lvl):
                end_segment = True
            if DBUG: # or True:
                do_DBUG("current_line-head:", is_head(current_line),
                        "current_line:", current_line,
                        "wrk_seg_def:", wrk_seg_def,
                        "match_hdr:", match_hdr,
                        "match_ln:", match_ln,
                        "wrk_ln_lvl:", wrk_ln_lvl,
                        "end_segment:", end_segment)

    # end while loop

    end_ln = wrk_ln - 1

    if key_is("type", ln_control, "LIST"):
        # print "-------------------------"
        if len(process_dict) > 0:

            ############################################
            # if there is something in process_dict
            # we need to add to process_list using
            # write_proc_dl
            # it will deal with source addition
            # etc.
            ############################################

            process_dict, process_list = write_proc_dl(kvs,
                                                       process_dict,
                                                       process_list)

        if DBUG:
            do_DBUG("seg:", seg, "adding from process_list")

        if check_type(seg[seg_name]) == "LIST":
            seg[seg_name].append(process_list)

        if DBUG:
            do_DBUG("seg_name:", seg_name,
                    "seg[seg_name]:", seg[seg_name])

    elif key_is("type", ln_control, "DICT"):
        seg[seg_name] = process_dict
        if DBUG:
            do_DBUG("Type is DICT",
                    "adding from process_dict",
                    "process_dict:", process_dict,
                    "seg_name:", seg_name,
                    "seg[seg_name]:", seg[seg_name])

    if DBUG:
        do_DBUG("<<==<<==<<==<<==<<==<<==<<==<<==<<",
                "returning end_ln:", end_ln,
                "wrk_ln:", wrk_ln,
                "end_segment:", end_segment,
                "wrk_segment:", wrk_segment,
                "type:", wrk_seg_def,
                "ln_control[type]:", to_json(ln_control),
                "returning dict(current_line):", to_json(seg),
                "from process_dict:", to_json(process_dict),
                "from process_list:", process_list,
                "save_to:", save_to,
                "len(save_to):", len(save_to),
                "<<==<<==<<==<<==<<==<<==<<==<<==<<", )
    if len(save_to) <= 1:
        save_to = seg[seg_name]
        if DBUG:
            do_DBUG("seg:", seg,
                    "save_to:", to_json(save_to))

    return end_ln, save_to, current_segment


###############################################################
###############################################################
###############################################################
###############################################################

def adjusted_level(lvl, match_ln):
    # lookup the level based on the max of source line lvl
    # and SEG_DEF matched level

    DBUG = False

    result = lvl
    if find_segment(combined_match(lvl, match_ln)):
        seg_info = get_segment(combined_match(lvl, match_ln))
        if key_is_in("level", seg_info):
            result = max(lvl, seg_info["level"])

    if DBUG:
        do_DBUG("Level(lvl):", lvl, "Result:", result,
                "Using match_ln:", to_json(match_ln))

    return result


def assign_key_value(line_dict, wrk_seg_def, kvs):
    # evaluate the line to get key and value

    full_line = line_dict["line"]
    kvs["ln"] = line_dict["key"]

    # print full_line
    line_source = full_line.split(":")
    if len(line_source) > 1:
        kvs["k"] = headlessCamel(line_source[0])
        kvs["v"] = line_source[1].lstrip()
        # lines with more than 1 : get truncated.
        # so lets make sure we ge the whole line
        kvs = get_rest_of_line(kvs, line_source)
        kvs["v"] = kvs["v"].rstrip()

    else:
        if line_dict["type"].upper() == "HEADER":
            kvs["k"] = wrk_seg_def["name"]
            if wrk_seg_def["type"] == "dict":
                kvs["v"] = {kvs["k"]: kvs["v"]}
            elif wrk_seg_def["type"] == "list":
                kvs["v"] = []
        else:
            # add to comments list
            if not kvs["comments"]:
                kvs["comments"] = [kvs["v"]]
            else:
                kvs["comments"].append(kvs["v"])
            kvs["k"] = "comments"
            kvs["v"] = full_line

    if "SOURCE" in kvs["k"].upper():
        kvs["k"] = headlessCamel(kvs["k"])
        kvs = set_source(kvs)

        # print "SET source:", kvs["source"]

    if len(kvs["k"]) > 2:
        if kvs["k"][2] == "/":
            # print "got the date line in the header"
            kvs["v"] = {"value": parse_time(full_line)}
            kvs["k"] = "effectiveTime"
            # segment[current_segment]={k: v}

    if "DATE" in kvs["k"].upper():
        kvs["v"] = parse_date(kvs["v"])

    if "DOB" == kvs["k"].upper():
        kvs["v"] = parse_date(kvs["v"])

    if "DOD" == kvs["k"].upper():
        kvs["v"] = parse_date(kvs["v"])

    # remove "/" in field names
    if "/" in kvs["k"]:
        kvs["k"] = kvs["k"].translate(None,"/")

    return kvs


def build_address(ln_list, wk_ln):
    # Build address block
    # triggered because current line has
    # k.upper() == "ADDRESSLINE1" or "ADDRESSTYPE"
    # so read until k.upper() == "ZIP"
    # then return address block and work_ln reached

    DBUG = False

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
            # look for key in address block
            address_block[k] = v
            end_block = False
            wk_ln += 1
        else:
            end_block = True

    # Check the format of the address block
    # sometimes the city, state, zip is entered in the addressLine1/2

    if len(address_block["city"] +
            address_block["state"] +
            address_block["zip"]) < 2:
        if DBUG:
            do_DBUG("Empty city, state, zip: ", len(address_block["city"] +
                                                    address_block[
                                                        "state"] +
                                                    address_block["zip"]))

        patch_address = (
            address_block["addressLine1"] + " " +   address_block[
                "addressLine2"]).rstrip()

        if address_block["zip"] == "":
            # if zip is empty check end of patch address for zip
            # if we have a zip+4 then the 5th character from end will be -
            if patch_address[-5] == "-":
                # We have a Zip + 4
                # so get last 10 characters
                address_block["zip"] = patch_address[-10:]
                patch_address = patch_address[1:-11]

            elif patch_address[-5:].isdigit():
                # are the last 5 characters digits?
                address_block["zip"] = patch_address[-5:]
                patch_address = patch_address[1:-6]

            else:
                # do nothing
                pass

            if address_block["zip"] != "" and address_block[
                    "state"] == "" and patch_address[-3] == " ":
                # We did something with the zip
                # so now we can test for " {State_Code}" at end of
                # patch_address
                # get two characters
                new_state = patch_address[-3:].lstrip().upper()
                if new_state in STATES:
                    # We got a valid STATE ID
                    # so add it to address_block
                    address_block["state"] = new_state
                    # then remove from patch_address
                    patch_address = patch_address[1:-3]

            if len(patch_address.rstrip()) > len(
                    address_block["addressLine1"]):
                # The zip and state were in Address Line 2
                # so we will update addressLine2
                address_line2 = patch_address[
                                (len(address_block["addressLine1"]) - 1):]
                address_line2.lstrip()
                address_line2.rstrip()
                address_block["addressLine2"] = address_line2
            else:
                # the zip and state came from addressLine1
                address_block["addressLine1"] = patch_address.rstrip()

    if DBUG:
        do_DBUG("ADDRESS BLOCK---------",
                to_json(address_block),
                "wk_ln:", wk_ln - 1)

    return address_block, wk_ln - 1


def check_type(check_this):
    # Check_this and return type

    result = "UNKNOWN"

    if isinstance(check_this, dict):
        result = "DICT"
    elif isinstance(check_this, list):
        result = "LIST"
    elif isinstance(check_this, tuple):
        result = "TUPLE"
    elif isinstance(check_this, basestring):
        result = "STRING"
    elif isinstance(check_this, bool):
        result = "BOOL"
    elif isinstance(check_this, int):
        result = "INT"
    elif isinstance(check_this, float):
        result = "FLOAT"

    return result


def combined_match(lvl, match_ln):
    # Get a "." joined match string to use to search SEG_DEF
    # lvl = number to iterate up to
    # match_ln = list to iterate through
    # return the combined String as combined_header
    # eg. patient.partAEffectiveDate

    DBUG = False

    ctr = 0
    combined_header = ""
    # print match_ln

    if DBUG:
        do_DBUG("lvl:", lvl, "match_ln:", match_ln,
                "combined_header:", combined_header)

    while ctr <= lvl:
        if ctr == 0:
            combined_header = match_ln[ctr]
        else:
            if match_ln[ctr] == None:
                pass
            else:
                combined_header = combined_header + "." + match_ln[ctr]

        ctr += 1

    if DBUG:
        do_DBUG("lvl:", lvl, "match_ln:", match_ln,
                "combined_header:", combined_header)

    return combined_header


def dict_in_list(ln_control):
    # if SEG_DEF type = list and sub_type = "dict"
    # return true

    DBUG = False

    result = False
    if ln_control["type"].upper() == "LIST":
        if ln_control["sub_type"].upper() == "DICT":
            result = True

    if DBUG:
        do_DBUG("ln_control:", to_json(ln_control),
                "result:", result)

    return result


def do_DBUG(*args, **kwargs):
    # basic debug printing function
    # if string ends in : then print without newline
    # so next value prints on the same line

    # inspect.stack()[1][3] = Function that called do_DBUG
    # inspect.stack()[1][2] = line number in calling function

    # print inspect.stack()
    print "####################################"
    print "In function:", inspect.stack()[1][3], "[", \
        inspect.stack()[1][2], "]"
    # print args

    # print six.string_types
    for i in args:
        if isinstance(i, six.string_types):
            if len(i) > 1:
                if i[-1] == ":":
                    print i,
                else:
                    print i
            else:
                print i
        else:
            print i
    print "####################################"

    return


def find_segment(title, exact=False):
    DBUG = False

    result = False
    ky = ""

    # cycle through the seg dictionary to match against title
    for ky in SEG_DEF:
        if exact is False:
            if title in ky["match"]:
                result = True
                break
        else:
            if ky["match"] == title:
                result = True
                break

    if DBUG:
        do_DBUG("title:", title,
                "match exact:", exact,
                "ky in SEG_DEF:", ky,
                "result:", result)

    return result


def get_dict_name(wrk_seg_def):
    # Get dict_name from wrk_seg_def
    # If no "dict_name" then return "name"

    DBUG = False

    if key_is_in("dict_name", wrk_seg_def):
        dict_name = wrk_seg_def["dict_name"]
    else:
        key_is_in("name", wrk_seg_def)
        dict_name = wrk_seg_def["name"]

    if DBUG:
        do_DBUG("wrk_seg_def:", to_json(wrk_seg_def),
                "dict_name:", dict_name)

    return dict_name


def get_level(ln):
    # Get level value from SEG_DEF Line

    result = None

    if key_is_in("level", ln):
        result = ln["level"]

    return result


def get_line_dict(ln, i):
    # Get the inner line dict from ln
    DBUG = False

    found_line = ln[i]
    extract_line = found_line[i]

    # fix for missing claim header line(s)
    if "Claim Number:" in extract_line["line"]:
        # we need to check the previous line which
        # should be "claimHeader". If it isn't we have a missing
        # header so change this line content type to "HEADER"
        prev_i = max(0, i - 1)
        prev_line = ln[prev_i][prev_i]

        if DBUG:
            do_DBUG("ln["+ str(prev_i)+"]:",
                    ln[prev_i],
                    prev_line)
        if prev_line["line"].upper() == "CLAIM HEADER" or \
                "SOURCE:" in prev_line["line"].upper():
            if DBUG:
                do_DBUG("We found claim Number with previous claimHeader")
            pass
        else:
            if DBUG:
                do_DBUG("MISSING PREVIOUS CLAIM HEADER",
                        "Extract line:", extract_line,
                        "Previous Line:", prev_line,
                        "Changing TYPE")
                extract_line["type"] = "HEADER"

    return extract_line


def get_rest_of_line(kvs, line_source):
    # Lines with multiple colons get truncated
    # so we need to rebuild the full value entry
    # line_source was split on ":" so we need to ad those back

    DBUG = False

    line_value = line_source[1]
    piece = 2

    if len(line_source) > 2:

        while piece < len(line_source):
            # skip the first item it will be the field name

            line_value = line_value + ":" + line_source[piece]
            piece += 1

    if DBUG:
        do_DBUG("piece:", piece, "line_value:", line_value,
                "Line_Source:", line_source)

    kvs["v"] = line_value.lstrip()

    return kvs


def get_segment(title, exact=False):
    # get the SEG_DEF record using title in Match

    DBUG = False

    result = {}
    ky = ""

    # cycle through the seg dictionary to match against title
    for ky in SEG_DEF:
        if exact == False:
            if title in ky["match"]:
                result = ky
                break
        else:
            if ky["match"] == title:
                result = ky
                break

    if DBUG:
        do_DBUG("title:", title,
                "match exact:", exact,
                "ky in SEG_DEF:", ky,
                "result:", result)

    return result


def headlessCamel(In_put):
    # Use this to format field names:
    # Convert words to title format and remove spaces
    # Remove underscores
    # Make first character lower case
    # result result

    DBUG = False

    Camel = ''.join(x for x in In_put.title() if not x.isspace())
    Camel = Camel.replace('_', '')

    result = Camel[0].lower() + Camel[1:len(Camel)]

    if DBUG:
        do_DBUG("In_put:", In_put, "headlessCamel:", result)

    return result


def is_body(ln):
    # Is line type = "BODY"

    DBUG = False

    result = False
    if key_is_in("type", ln):
        if ln["type"].upper() == "BODY":
            result = True

    if DBUG:
        do_DBUG("is_body:", result)

    return result


def is_eol(ln, lst):
    # Are we at the end of the list
    # len(list) - 1

    result = False

    if ln >= len(lst) - 1:
        # line is >= items in list
        result = True

    return result


def is_head(ln):
    # Is line type = "HEADER" in ln

    DBUG = False

    result = False

    if key_is_in("type", ln):

        if DBUG:
            do_DBUG("Matching HEAD in:", ln["type"])

        if "HEAD" in ln["type"].upper():
            # match on "HEAD", "HEADING" or "HEADER"
            result = True

    if DBUG:
        do_DBUG("is_header:", result)

    return result


def is_multi(ln_dict):
    # Check value of "Multi" in ln_dict

    DBUG = False

    result = False

    if key_is_in("multi", ln_dict):
        multi = ln_dict["multi"].upper()
        if multi == "TRUE":
            result = True
    else:
        result = False

    if DBUG:
        do_DBUG("result:", result,
                "ln_dict:", to_json(ln_dict))

    return result


def key_is(ky, dt, val):
    # if KY is in DT and has VAL

    DBUG = False

    result = False

    if ky in dt:
        if dt[ky].upper() == val.upper():
            result = True

    if DBUG:
        do_DBUG("ky:", ky,
                "dict:", to_json(dt),
                "val:", val,
                "result:", result)

    return result


def key_is_in(ky, dt):
    # Check if key is in dict

    DBUG = False

    result = False
    if ky in dt:
        result = True

    if DBUG:
        do_DBUG("ky:", ky,
                "dict:", to_json(dt),
                "result:", result)

    return result


def key_is_in_subdict(ky, dt):
    # Check if key is in dict

    DBUG = False

    result = False

    # print "Size of dict-dt:", len(dt)

    for ctr in dt:
        # print "dt["+str(ctr)+"]", dt[ctr]
        if ky in dt[ctr]:
            key = dt[ctr]
            # print "key:", ky, " in ", dt[ctr]
            result = True
            break

    if not result:
        for key in dt.keys():
            # print "key:", key
            if ky in key:
                # print "key:", key
                result = True
                break

            elif isinstance(key, dict):
                for subkey, subval in key.items():
                    # print "subkey:", subkey, "subval:", subval
                    if ky in subkey:
                        result = True
                        break

                        # end of for subkey
    # end of for key
    if DBUG:
        do_DBUG("ky:", ky,
                "key:", key,
                "dict:", to_json(dt),
                "result:", result)

    return result


def key_value(ky, dt):
    # check if key is in dict and
    # return the value of key or "" if not found
    # done to avoid key errors

    result = ""

    DBUG = False

    if ky in dt:
        result = dt[ky]

    if DBUG:
        do_DBUG("ky:", ky,
                "dict:", to_json(dt),
                "result:", result)

    return result


def overide_fieldname(lvl, match_ln, current_fld):
    # Lookup line  in SEG_DEF using match_ln[lvl]
    # look for "name" or "field"
    # if no match return current_fld
    # else return name or field
    # if name and field defined use field

    result = current_fld

    title = combined_match(lvl, match_ln)
    if find_segment(title):
        tmp_seg_def = get_segment(title)
        if key_is_in("field", tmp_seg_def):
            result = tmp_seg_def["field"]
        elif key_is_in("name", tmp_seg_def):
            result = tmp_seg_def["name"]

        if DBUG:
            do_DBUG("lvl:", lvl, "Match_ln", to_json(match_ln),
                    "title:", title, "tmp_seg_def", to_json(tmp_seg_def),
                    "Result:", result)

    return result


def parse_date(d):
    # convert date to json format

    DBUG = False

    if DBUG:
        do_DBUG("Date to parse:", d)
    result = ""

    d = d.strip()
    if len(d) > 0:
        # print d
        date_value = datetime.strptime(d, "%m/%d/%Y")
        result = date_value.strftime("%Y%m%d")

    if DBUG:
        do_DBUG("Result:", result)

    return result


def parse_time(t):
    # convert time to  json format

    DBUG = False

    if DBUG:
        do_DBUG("Time to parse:", t)
    t = t.strip()
    time_value = datetime.strptime(t, "%m/%d/%Y %I:%M %p")
    # print time_value
    result = time_value.strftime("%Y%m%d%H%M%S+0500")

    if DBUG:
        do_DBUG("Result:", result)

    return result


def segment_prefill(wrk_seg_def, segment_dict):
    # Receive the Segment information for a header line
    # get the seg["pre"] and iterate through the dict
    # assigning to segment_dict
    # First we reset the segment_dict as an OrderedDict

    DBUG = False

    if len(segment_dict) > 0:

        if DBUG:
            print "Pre-fill- segment_dict:", segment_dict, "NOT EMPTY"

        pass
    else:
        segment_dict = collections.OrderedDict()

    if DBUG:
        do_DBUG("seg", to_json(wrk_seg_def))

    current_segment = wrk_seg_def["name"]

    if key_is_in("pre", wrk_seg_def):

        if "pre" in wrk_seg_def:
            pre = wrk_seg_def["pre"]
            for pi, pv in pre.iteritems():
                segment_dict[pi] = pv

    if DBUG:
        do_DBUG("Current_Segment:", current_segment,
                "segment_dict", segment_dict)

    return current_segment, segment_dict


def set_source(kvs):
    # Set the source of the data

    result = kvs["source"]
    if kvs["k"].upper() == "SOURCE":
        # print "Found Source: [%s:%s]" % (key,value)
        if kvs["v"].upper() == "SELF-ENTERED":
            result = "patient"
            kvs["v"] = result

        elif kvs["v"].upper() == "MYMEDICARE.GOV":
            result = "MyMedicare.gov"
            kvs["v"] = result

        else:
            result = kvs["v"].upper()
        # print "[%s]" % result
        kvs["source"] = result

    return kvs


def setup_header(ln_ctrl, wrk_ln_dict):
    DBUG = False

    wrk_add_dict = {}
    segment_name = ln_ctrl["name"]
    returned_segment = ""

    # sub_kvs = {"k": "", "v": "", "source": "", "comments": [], "ln": 0}

    # sub_kvs = assign_key_value(wrk_ln_dict["line"], sub_kvs)

    if key_is_in("type", ln_ctrl):
        if ln_ctrl["type"].lower() == "list":
            wrk_add_dict[segment_name] = []
        elif ln_ctrl["type"].lower() == "dict":
            wrk_add_dict[segment_name] = collections.OrderedDict()
            if key_is_in("pre", ln_ctrl):
                returned_segment, \
                wrk_add_dict[segment_name] = segment_prefill(ln_ctrl,
                    {})
        else:
            wrk_add_dict[segment_name] = wrk_ln_dict["line"]

    if DBUG:
        do_DBUG("Assigning Header========================",
                # "Sub_KVS:", sub_kvs,
                "from wrk_ln_dict:", to_json(wrk_ln_dict),
                "using ln_ctrl:", to_json(ln_ctrl),
                "returning wrk_add_dict:", to_json(wrk_add_dict))

    return wrk_add_dict


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

    return k, v


def to_json(items):
    """
    to_json
    pretty json format with indent = 4
    """
    itemsjson = json.dumps(items, indent=4)
    return itemsjson


def update_match(lvl, txt, match_ln):
    # Update the match_ln list
    # lvl = number position in match_ln
    # txt = line to check (received in headlessCamel format)
    # match_ln = list

    DBUG = False

    line = txt.split(":")
    if len(line) > 1:
        keym = line[0]

    else:
        keym = txt

    # get the line or the line up to the ":"
    # set the lvl position in the match_ln list
    match_ln[lvl] = keym

    if DBUG:
        do_DBUG("update_match(lvl, txt, match_ln)", lvl, txt, match_ln,
                "keym:", keym, "match_ln[" + str(lvl) + "]:",
                match_ln[lvl])

    return match_ln


def update_save_to(target, src, key, val_fld):
    # Test the target and update with source

    DBUG = False

    target_type = check_type(target)
    save_to = target

    if DBUG:
        do_DBUG("save_to:", save_to,
                "using source:", src,
                "key:", key,
                "val_fld:", val_fld,
                "and target:", target,
                "with target_type:", target_type)

    if target_type == "DICT":
        # print save_to[key]
        if key_is_in(key, save_to):
            if check_type(save_to[key]) == "LIST":
                save_to[key] = src[val_fld]
        else:
            save_to[key] = src[val_fld]

    elif target_type == "LIST":
        save_to = src[val_fld]
    elif target_type == "TUPLE":
        save_to[key] = {key: src[val_fld]}
    elif target_type == "STRING":
        string_to_write = src[val_fld]
        save_to = src[val_fld]
    else:
        save_to[key] = src[val_fld]

    if DBUG:
        do_DBUG("returning save_to:", save_to,
                "using source:", src,
                "and val_fld:", val_fld,
                "and target:", target,
                "with target_type:", target_type)

    return save_to


def write_comment(wrk_add_dict, kvs):
    # if value is assigned to comments we need to check
    # if comments already present
    # if so, add to the list

    DBUG = False

    if DBUG:
        do_DBUG("IN WRITE COMMENTS", "wrk_add_dict:",
                to_json(wrk_add_dict), "kvs:", to_json(kvs))

    if not key_is_in(kvs["k"], wrk_add_dict):
        # print kvs["k"]," NOT in wrk_add_dict"
        # so initialize the comments list

        wrk_add_dict[kvs["k"]] = []

    else:
        if isinstance(wrk_add_dict[kvs["k"]], basestring):
            tmp_comment = wrk_add_dict[kvs["k"]]
            print "tmp_comment:", tmp_comment
            # get the comment
            wrk_add_dict[kvs["k"]] = []
            # initialize the list
            wrk_add_dict[kvs["k"]].append(tmp_comment)

    # Now add the comment
    wrk_add_dict[kvs["k"]].append(kvs["v"])

    # kvs["comments"].append(kvs["v"])

    if DBUG:
        do_DBUG("k:", kvs["k"], "v:", kvs["v"],
                "wrk_add_dict[" + kvs["k"] + "]:",
                wrk_add_dict[kvs["k"]],
                "wrk_add_dict:", to_json(wrk_add_dict))

    return wrk_add_dict


def write_proc_dl(kvs, process_dict, process_list):
    # standardize the update of Process_dict and process_list

    DBUG = False

    # Write source and comments to the dict
    process_dict = write_source(kvs, process_dict)
    # how long is process_list?
    last_item = len(process_list) - 1

    if key_is_in("details", process_dict):
        if DBUG:
            do_DBUG("COUNT OF LIST ITEMS:", last_item)

        process_list[max(last_item, 0)]["details"] = [process_dict]

    elif key_is_in("lineNumber", process_dict):
        if DBUG:
            do_DBUG("COUNT of LIST ITEMS FOR EXTRA LINES:", last_item)

        if key_is_in("details", process_list[max(last_item, 0)]):
            process_list[max(last_item, 0)]["details"].append(process_dict)

        else:
            process_list[max(last_item, 0)]["details"] = [process_dict]

    else:
        process_list.append(process_dict)
        if DBUG:
            do_DBUG("details NOT found in process_dict",
                    "appended process_dict to process_list",
                    process_list)

    return process_dict, process_list


def write_save_to(save_to, pd):
    # iterate through dict and add to save_to

    """

    :param save_to:
    :param pd:
    :return:
    """
    DBUG = False

    if DBUG:
        do_DBUG("pd:", pd)

    i = 0
    for item in pd.items():
        key = item[0]
        # print "key:", key
        val = item[1]
        # print "item:", item[1]
        save_to[key] = item[1]

    if DBUG:
        do_DBUG("pd:", pd,
                "save_to:", to_json(save_to))

    return save_to


def write_segment(itm, sgmnt, sgmnt_dict, ln_list, multi):
    # Write the segment to items dict

    DBUG = False

    if DBUG:
        do_DBUG("Item:", itm, "Writing Segment:", sgmnt,
                "Writing dict:", sgmnt_dict,
                "Multi:", multi,
                "ln_list:", ln_list)
    if multi:
        ln_list.append(sgmnt_dict)
        # print "Multi List:", ln_list
        itm[sgmnt] = ln_list
    else:
        itm[sgmnt] = sgmnt_dict

    return itm, sgmnt_dict, ln_list


def write_source(kvs, dt):
    # Write source and comments to dt

    DBUG = False

    if DBUG:
        do_DBUG("kvs:", kvs)

    if kvs["comments"]:
        # write comments
        dt["comments"] = kvs["comments"]
        # clear down comments
        kvs["comments"] = []

    if kvs["source"]:
        dt["source"] = kvs["source"]

    return dt

