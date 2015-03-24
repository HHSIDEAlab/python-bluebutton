"""
python-bluebutton
FILE: cms_parser_utilities
Created: 3/9/15 5:34 PM


"""
__author__ = 'Mark Scrimshire:@ekivemark'

from datetime import datetime, date, timedelta

import json
import collections
import inspect
import six

from file_def_cms import SEG_DEF
from usa_states import STATES

DBUG = False


def process_header(strt_ln, ln_control, strt_lvl, ln_list):
    # Input:
    # strt_ln = current line number in the dict
    # ln_control = entry from SEG_DEF for the start_ln
    # match_ln = list array to build a breadcrumb match setting
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

    wrk_add_dict = collections.OrderedDict()

    # Setup
    # we dropped in to this function because we found a SEG_DEF dict
    # which was loaded in to ln_control.

    segment = ln_control["name"]

    wrk_ln_dict = get_line_dict(ln_list, strt_ln)
    # Load wrk_ln_dict ready for evaluating line in setup_header

    wrk_add_dict = setup_header(ln_control,wrk_ln_dict )
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
    #        "line": "MYMEDICARE.GOV PERSONAL HEALTH INFORMATION",
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

    # TODO: Fix Funky errors [Family History] - some entries not written
    # FIXED: Preventive Services - Some items not added
    # FIXED: Providers - last entry does not get source info
    # FIXED: Providers - Fields not in order
    # FIXED: Pharmacies - Last record missing Pharmacy Name
    # FIXED: Pharmacies - last entry does not get source info
    # TODO: category dict written after insurance section
    # TODO: Employer Subsidy Header not written
    # TODO: Primary Insurance Header not written
    # TODO: Other Insurance Header not written
    # TODO: Claim Details need to be embedded inside Claim Header
    # TODO: Multiple Claims Headers and Details not handled
    # TODO: Claims - First Header and Last Claim Detail written
    # TODO: Fix Time fields (minutes dropped after colon)

    # TODO: clean up write section - break out to more sub-functions

    current_segment = seg_name
    seg_type = check_type(seg[seg_name])
    end_segment = False
    wrk_ln = strt_ln

    wrk_seg_def = {}

    wrk_ln_lvl = strt_lvl
    wrk_ln_head = False
    kvs = {"k": "", "v": "", "source": "", "comments": []}
    wrk_segment = seg_name
    multi = key_is("multi", ln_control, "TRUE")

    # Update match_ln with headers name from SEG_DEF (ie. ln_control)
    match_ln = update_match(strt_lvl, seg_name, match_ln)

    save_to = seg[seg_name]
    print "pre-load the data passed in to ", seg_type, "  <<<<<<<<<<<<<<<<"
    print "seg[" + seg_name + "]:",to_json(seg[seg_name])

    process_dict = collections.OrderedDict()
    process_list = []

    # get current line
    current_line = get_line_dict(ln_list, wrk_ln)

    if DBUG:
        do_DBUG(">>==>>==>>==>>==>>==>>==>>==>>==>>==>>==>>",
                "type:", seg_type,
                "seg", to_json(seg),
                "seg_name:", seg_name,
                "ln_control:", to_json(ln_control),
                "strt_lvl:", strt_lvl,
                "match_ln:", match_ln,
                ">>==>>==>>==>>==>>==>>==>>==>>==>>==>>==>>")

    while not end_segment and (wrk_ln <= len(ln_list)-1):
        if wrk_ln == len(ln_list)-1:
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
        wrk_lvl = current_line["level"]

        match_ln = update_match(wrk_lvl,
                                headlessCamel(current_line["line"]),
                                match_ln)
        match_hdr = combined_match(wrk_lvl, match_ln)
        # Find segment using combined header

        is_line_seg_def = find_segment(match_hdr, True)
        # Find SEG_DEF with match exact = True

        if DBUG:
            do_DBUG("*****************PRESET for line***********",
                    "wrk_lvl:", wrk_lvl,
                    "match_ln:", match_ln,
                    "match_hdr:", match_hdr,
                    "is_line_seg_def:", is_line_seg_def,
                    "wrk_seg_def:", wrk_seg_def)

        if is_line_seg_def:
            # We found an entry in SEG_DEF using match_hdr

            wrk_seg_def = get_segment(match_hdr, True)
            # We found a SEG_DEF match with exact=True so Get the SEG_DEF

            match_ln = update_match(wrk_lvl, wrk_seg_def["name"], match_ln)
            # update the name in the match_ln dict

            # we also need to check the lvl assigned to the line from
            # SEG_DEF
            wrk_ln_lvl = wrk_seg_def["level"]
            multi = key_is("multi", wrk_seg_def, "TRUE")

            if DBUG:
                do_DBUG("is_line_seg_def:", is_line_seg_def,
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
                print "DEALING WITH NEW HEADER:", current_line["line"]

                # set wrk_ln_head = True
                wrk_ln_head = True
                wrk_lvl = get_level(wrk_seg_def)

                if (wrk_lvl == strt_lvl):
                    # We must be at the start of a new segment
                    end_segment = True
                    # we also need to step the wrk_ln counter back by 1
                    wrk_ln -= 1

                else:
                    # I think we need to go recursively in to
                    # process_block because we may have a lower level
                    # header (eg. Claims details)
                    # pass
                    if DBUG:
                        do_DBUG("wrk_lvl:", wrk_lvl, "strt_lvl:", strt_lvl,
                                "wrk_ln_head:", wrk_ln_head,
                                "processing:", to_json(current_line),
                                "with wrk_seg_def:", to_json(wrk_seg_def))

            # if DBUG:
            #    do_DBUG("wrk_lvl:", wrk_lvl, "Strt_lvl:", strt_lvl,
            #            "wrk_ln:", wrk_ln)

        else:
            # NOT is-line-seg_def
            wrk_seg_def = ln_control

        # Get key and value
        kvs = assign_key_value(current_line["line"],
                               wrk_seg_def,
                               kvs)

        if DBUG:
            do_DBUG("wrk_lvl:",wrk_lvl, "match_hdr:", match_hdr,
                    "kvs:",to_json(kvs),
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
            wrk_segment, process_dict = segment_prefill(wrk_seg_def, process_dict)

            if DBUG:
                do_DBUG("Just ran segment_prefill",
                        "wrk_segment:", wrk_segment,
                        "process_dict:", to_json(process_dict),
                        "process_list:", process_list)

            # Do we need to override the key using field or name
            # from SEG_DEF?

            # pass in match_ln, match_hdr, and wrk_lvl to allow
            # Override to be checked

            if ("SOURCE" in kvs["k"].upper()):
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
                #return Address dict and work_ln reached

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

                print "comments - save_to:", save_to

                save_to = update_save_to(save_to, process_dict, kvs["k"])
                print "After Comments Save to:", save_to, "process_dict:", process_dict

                if DBUG:
                    do_DBUG("is_line_seg_def:", is_line_seg_def,
                            "wrk_seg_def", wrk_seg_def,
                            "wrk_ln:", wrk_ln,
                            "kvs:", to_json(kvs),
                            "current_line:", current_line)

            if multi:
                print "******************************"
                print "MULTI:", multi
                if key_is("type", wrk_seg_def, "LIST"):
                    if key_is("sub_type", wrk_seg_def, "DICT"):
                        print "LIST and sub_type: DICT"
                        print "save_to:", save_to
                        print "process_dict:", process_dict
                        print "process_list:", process_list
                        print "kvs:", kvs
                        if kvs["k"] in process_dict:
                            print "k:", kvs["k"], " in ", process_dict
                            # write the source  and comments first
                            process_dict = write_source(kvs, process_dict)
                            print "process_dict:", process_dict
                            # Append to the list
                            process_list.append(process_dict)
                            print "process_list:", to_json(process_list)
                            # Now clear down the dict and
                            # add the new item
                            process_dict = collections.OrderedDict()
                            if not kvs["k"].upper() == "COMMENTS":
                                print "skipping comments"
                                process_dict[kvs["k"]] = kvs["v"]
                            print "process_dict (after write):", process_dict
                        else:
                            print "kvs[k] not in process_dict", kvs, process_dict
                            process_dict[kvs["k"]] = kvs["v"]
                    else:
                        if key_is_in("sub_type", wrk_seg_def):
                            print "wrk_seg_def sub_type:", \
                                wrk_seg_def["sub_type"]

                        process_dict[kvs["k"]] = [kvs["v"]]
                        print "process_dict:", process_dict
                        save_to = write_save_to(save_to, process_dict)

                elif key_is("type", wrk_seg_def, "DICT"):
                    print "wrk-seg_def:", wrk_seg_def
                    if key_is("sub_type", wrk_seg_def, "DICT"):
                        print "DICT and sub_type: DICT:", kvs
                        if DBUG or True:
                            do_DBUG("WHAT GETS WRITTEN HERE?",
                            "ln_control:", to_json(ln_control),
                            "wrk_seg_def:", to_json(wrk_seg_def),
                            "current_line:", to_json(current_line),
                            "process_dict:", to_json(process_dict),
                            "process_list:", process_list)

                        # Write what
                        process_dict[wrk_seg_def["name"]] = kvs["v"]
                        print "just wrote process_dict:", process_dict

                    else:
                        print "No sub_type"
                        if key_is_in("sub_type", wrk_seg_def):
                            print "type: DICT and sub_type:", \
                                wrk_seg_def["sub_type"]
                        else:
                            print "writing to process_dict:", process_dict   # homePhone workPhone

                            # type: dict
                            # dict_name: phone
                            # field : home
                            # k: homePhone v = ""
                            # needs to get written as
                            # phone {"home": "", "work": "", "mobile": ""}
                            # process_dict[wrk_seg_def["dict_name"]] = {wrk_seg_def["field"]: kvs["v"]
                            # follow on elements need to check:
                            # wrk_seg_def["dict_name"] or kvs["k"]

                            if key_is_in_subdict(kvs["k"], process_dict):
                                # write the source first
                                print "roll a new process_dict"
                                process_dict = write_source(kvs, process_dict)
                                # Append to the list
                                process_list.append(process_dict)
                                # Now clear down the dict and
                                # add the new item
                                process_dict = collections.OrderedDict()
                                process_dict[kvs["k"]] = kvs["v"]

                            print "didn't find:", kvs["k"]                       # homePhone workPhone
                            print "is_line_seg_def:", is_line_seg_def

                            if is_line_seg_def and key_is_in("dict_name",wrk_seg_def):
                                print "got dict_name:", wrk_seg_def["dict_name"] # homePhone workPhone
                                if not key_is_in(wrk_seg_def["dict_name"], process_dict):
                                    print "no dict_name"                         # homePhone workPhone

                                    process_dict[wrk_seg_def["dict_name"]] = {wrk_seg_def["name"]: kvs["v"]}
                                    # process_dict[kvs["k"]] = kvs["v"]
                                else:
                                    print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"
                                    print "updating process_dict:", process_dict
                                    print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"

                                    print "with kvs:", kvs
                                    # process_dict[wrk_seg_def["dict_name"]] =kvs["v"]
                                    if check_type(process_dict[wrk_seg_def["dict_name"]]) == "DICT":
                                        process_dict[wrk_seg_def["dict_name"]].update({wrk_seg_def["name"]: kvs["v"]})
                                    else:
                                        process_dict[wrk_seg_def["dict_name"]] =kvs["v"]
                            else:
                                print "didn't get dict_name:", kvs
                                #process_dict[kvs["k"]] = kvs["v"]
                                save_to[kvs["k"]] = kvs["v"]
                                process_dict.update({kvs["k"]:kvs["v"]})
                                print "process_dict updated to:", process_dict

                else:
                    if key_is_in("type", wrk_seg_def):
                        print "wrk-seg_def:", wrk_seg_def["type"]

            else: # not multi
                if key_is("type", wrk_seg_def, "DICT"):
                    print "Multi:", multi, " and type: DICT"
                    if kvs["k"].upper() == "COMMENTS" and \
                            key_is_in("comments", save_to):
                            pass
                    else:
                        if not is_line_seg_def:
                            # We have no special processing rules for
                            # this line
                            print "is_line_seg_def:", is_line_seg_def, "kvs:", kvs
                            save_to[kvs["k"]] = kvs["v"]

                        elif key_is_in("dict_name", wrk_seg_def):
                            print "processing:", wrk_seg_def["dict_name"], kvs
                            print "save_to:", save_to
                            if key_is_in(wrk_seg_def["dict_name"], save_to):
                                save_to[wrk_seg_def["dict_name"]].update({kvs["k"]:
                                                                          kvs["v"]})
                            else:
                                save_to[wrk_seg_def["dict_name"]] = \
                                    {kvs["k"]: kvs["v"]}
                        else:
                            save_to[kvs["k"]] = kvs["v"]

                if key_is("type", wrk_seg_def, "LIST"):
                    print "Multi:", multi, " and type: LIST"
                    print "save_to:", to_json(save_to)
                    save_to = update_save_to(save_to, kvs, "k")
                    # save_to.extend([kvs["k"],kvs["v"]])

                if DBUG:
                    do_DBUG("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",
                            "WHAT GETS WRITTEN HERE?",
                            "MULTI:", multi,
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
            if is_head(current_line):
                end_segment = True


    # end while loop

    end_ln = wrk_ln - 1


    if key_is("type", ln_control, "LIST"):
        print "-------------------------"
        if len(process_dict) > 0:
            print "adding dict to list"
            print ""
            if not key_is_in("source", process_dict):
                print "adding source", kvs["source"]
                process_dict["source"] = kvs["source"]
            process_list.append(process_dict)
        print "seg:", seg
        print "adding from process_list"
        seg[seg_name].append(process_list)
        print seg[seg_name]
        pass
    elif key_is("type", ln_control, "DICT"):
        print "adding from process_dict"
        seg[seg_name] = process_dict
        pass
    if DBUG:
        do_DBUG("<<==<<==<<==<<==<<==<<==<<==<<==<<",
                "returning end_ln:", end_ln,
                "wrk_ln:", wrk_ln,
                "wrk_segment:", wrk_segment,
                "type:", wrk_seg_def,
                "ln_control[type]:", to_json(ln_control),
                "returning dict(current_line):", to_json(seg),
                "from process_dict:", to_json(process_dict),
                "from process_list:", process_list,

                "<<==<<==<<==<<==<<==<<==<<==<<==<<",)
    # print "How long is seg:", len(seg[seg_name])
    if len(save_to) == 1:
        print "nothing in save_to"

        save_to = seg[seg_name]
        print "seg:", seg


    return end_ln, save_to, current_segment


def process_block(strt_ln, ln_control, match_ln, strt_lvl,
                  ln_list, seg, seg_name):
    # Input:
    # strt_ln = current line number in the dict
    # ln_control = entry from SEG_DEF for the start_ln
    # match_ln = list array to build a breadcrumb match setting
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
    # seg = dict returned from process_header
    # seg_name = dict key in seg returned from process_header

    current_segment = seg_name

    seg_type = check_type(seg[seg_name])

    if DBUG:
        do_DBUG(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",
                "type:", seg_type,
                "seg", to_json(seg),
                "seg_name:", seg_name,
                "ln_control:", to_json(ln_control),
                "strt_lvl:", strt_lvl,
                "match_ln:", match_ln,
                ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    end_segment = False
    wrk_lvl = strt_lvl
    wrk_ln = strt_ln
    wrk_ln_lvl = strt_lvl
    # Wrk_ln_lvl is the value returned from a SEG_DEF match in the
    # while loop

    wrk_ln_dict = {}
    wrk_ln_head = True
    wrk_seg_def = {}
    kvs = {"k": "", "v": "", "source": ""}

    wrk_add_list = []
    wrk_add_dict = collections.OrderedDict(seg[seg_name])
    wrk_segment = seg_name

    is_line_seg_def = True

    # Handle Multiple Values in a segment
    # get from ln_control
    multi = is_multi(ln_control)

    # set match_ln to use name from ln_control for matching in SEG_DEF
    match_ln = update_match(strt_lvl, seg_name, match_ln)

    # use a dict to save multiple dict blocks
    save_add_dict = collections.OrderedDict()
    save_add_list = []

    # Setup
    segment = collections.OrderedDict()
    # we dropped in to this function because we found a SEG_DEF dict
    # which was loaded in to ln_control.
    wrk_ln_dict = get_line_dict(ln_list, wrk_ln)


    while not end_segment and (wrk_ln <= len(ln_list)-1):
        if wrk_ln == len(ln_list)-1:
            end_segment = True

        # not at end of file

        if DBUG:
            do_DBUG(">>>>>TOP of while loop",
                    "wrk_ln:", wrk_ln,
                    "wrk_ln_dict:", to_json(wrk_ln_dict),
                    "match_ln:", match_ln,
                    "wrk_add_dict:", to_json(wrk_add_dict))

        # update the match string in match_ln
        wrk_lvl = wrk_ln_dict["level"]

        match_ln = update_match(wrk_lvl,
                                headlessCamel(wrk_ln_dict["line"]),
                                match_ln)
        match_hdr = combined_match(wrk_lvl, match_ln)


        is_line_seg_def = find_segment(match_hdr, True)
        # Find SEG_DEF with match exact = True
        if DBUG:
            do_DBUG("wrk_lvl:",wrk_lvl, "match_hdr:", match_hdr,
                    "is_line_seg_def:", is_line_seg_def,
                    "wrk_add_dict:", to_json(wrk_add_dict))

        if is_line_seg_def:
            print "in is_line_seg_def=", is_line_seg_def
            # We found an entry in SEG_DEF using match_hdr

            wrk_seg_def = get_segment(match_hdr, True)
            # We found a SEG_DEF match with exact=True so Get the SEG_DEF
            match_ln = update_match(wrk_lvl, wrk_seg_def["name"], match_ln)
            # update the name in the match_ln dict
            # we also need to check the lvl assigned to the line from
            # SEG_DEF
            wrk_ln_lvl = wrk_seg_def["level"]

            # if the line is a HEADER line we need to setup the dict


            # and set wrk_ln_head to True
            wrk_ln_head = True

            if DBUG:
                do_DBUG("working with:", to_json(wrk_seg_def),
                        "(wrk_seg_def)",
                        "using match_ln:", match_ln,
                        "processing:", to_json(wrk_ln_dict),
                        "wrk_add_dict:", to_json(wrk_add_dict))

            if (wrk_ln != strt_ln) and (is_head(wrk_ln_dict)):
                # we found a new header
                # We have to deal with claims lines and claims headers
                # within claims. They have a different level value
                # So test for level = strt_lvl
                print "DEALING WITH NEW HEADER:", wrk_ln_dict["line"]

                # set wrk_ln_head = True
                wrk_ln_head = True
                wrk_lvl = get_level(wrk_seg_def)

                if (wrk_lvl == strt_lvl):
                    # We must be at the start of a new segment
                    end_segment = True
                    # we also need to step the wrk_ln counter back by 1
                    wrk_ln -= 1

                else:
                    # I think we need to go recursively in to
                    # process_block because we may have a lower level
                    # header (eg. Claims details)
                    pass
                    if DBUG:
                        do_DBUG("wrk_lvl:", wrk_lvl, "strt_lvl:", strt_lvl,
                                "wrk_ln_head:", wrk_ln_head,
                                "processing:", to_json(wrk_ln_dict),
                                "with wrk_seg_def:", to_json(wrk_seg_def))

            if DBUG:
                do_DBUG("wrk_lvl:", wrk_lvl, "Strt_lvl:", strt_lvl,
                        "wrk_ln:", wrk_ln)
        else:
            is_line_seg_def = False

        if not end_segment:
            # We need to process the line

            if key_is_in("pre", wrk_seg_def):
                # assign "pre" values from SEG_DEF
                # to work_add_dict
                wrk_segment, wrk_add_dict = segment_prefill(wrk_seg_def)

                if DBUG:
                    do_DBUG("Just ran segment_prefill",
                            "wrk_segment:", wrk_segment,
                            "wrk_ad_dict:", to_json(wrk_add_dict))

            # Now evaluate Keys and Values
            # Do we need to override the key using field or name
            # from SEG_DEF?
            # pass in match_ln, match_hdr, and wrk_lvl to allow
            # Override to be checked

            kvs = assign_key_value(wrk_ln_dict["line"],
                                   wrk_seg_def,
                                   kvs)

            # Now we check if we are dealing with an address block
            if ("ADDRESSLINE1" in kvs["k"].upper()) or \
                    ("ADDRESSTYPE" in kvs["k"].upper()):
                # Build an Address Block
                # By reading the next lines
                # until we find "ZIP"
                #return Address dict and work_ln reached

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
                wrk_add_dict = write_comment(wrk_add_dict, kvs)

                if DBUG:
                    do_DBUG("is_line_seg_def:", is_line_seg_def,
                            "wrk_seg_def", wrk_seg_def,
                            "wrk_ln:", wrk_ln,
                            "kvs:", to_json(kvs),
                            "wrk_add_dict:", wrk_add_dict)

            elif is_line_seg_def:
                if multi:
                    print "Multi:", multi
                    if key_is_in_subdict(kvs["k"], wrk_add_dict):
                        # Check if field is already used
                        # If it is and we could have multiple items
                        # then we need to save wrk_add_dict
                        # to save_add_dict first and
                        # clear down wrk_add_dict
                        if DBUG:
                            do_DBUG("items in save_add_dict:",
                                    len(save_add_dict), "saved:",
                                    to_json(save_add_dict),
                                    "wrk_add:", to_json(wrk_add_dict))
                        save_add_dict.update({len(save_add_dict)+1: wrk_add_dict})
                        wrk_add_dict = collections.OrderedDict()
                        if DBUG:
                            do_DBUG("Updated Saved:", to_json(save_add_dict))
                    else:
                        if DBUG:
                            do_DBUG("Multi but no entry yet:", multi,
                                    "wrk_add_dict:", to_json(wrk_add_dict),
                                    "save_add_dict:", to_json(save_add_dict))
                        pass

                if wrk_seg_def["type"] == "list":
                    print "dealing with list"
                    if key_is_in_subdict(kvs["k"], wrk_add_dict):
                        # save the dict ot a list
                        save_add_list.append(wrk_add_dict)
                        wrk_add_dict = []
                    else:
                        # initialize the list and then append the value
                        if DBUG:
                            do_DBUG("wrk_ln_head:",wrk_ln_head,
                                    "wrk_add_dict:", to_json(wrk_add_dict),
                                    "kvs:", kvs)

                        if wrk_ln_head:
                            wrk_add_dict[kvs["k"]] = [kvs["v"]]
                        else:
                            print "NOT A HEADER SO INITIALIZE and append"
                            wrk_add_dict[seg_name][kvs["k"]] = []
                            wrk_add_dict[seg_name][kvs["k"]].append(kvs["v"])

                elif wrk_seg_def["type"] == "dict":
                    print "dealing with dict"
                    print to_json(wrk_seg_def)

                    wrk_d_nam = get_dict_name(wrk_seg_def)
                    if wrk_d_nam not in wrk_add_dict:
                        wrk_add_dict[wrk_d_nam] = collections.OrderedDict()

                    wrk_add_dict[wrk_d_nam].update({kvs["k"]: kvs["v"]})
            else:
                # if not wrk_ln_head:
                print "Not a comment and is_line_seg_def:", is_line_seg_def
                if key_is_in_subdict(kvs["k"], wrk_add_dict):
                    print "wrk_add_dict:",to_json(wrk_add_dict)
                    if isinstance(wrk_add_dict[kvs["k"]], basestring):
                        wrk_add_dict[kvs["k"]] = kvs["v"]
                    elif isinstance(wrk_add_dict[kvs["k"]], dict):
                        wrk_add_dict[kvs["k"]] = {kvs["k"]: kvs["v"]}
                    else:
                        wrk_add_dict[kvs["k"]].append(kvs["v"])
                else:
                    print kvs["k"], " key not found in wrk_add_dict"
                    if kvs["k"] == "source":
                        # skip source
                        pass
                    elif dict_in_list(wrk_ln_dict):
                        print "dict within list"
                        if key_is_in(kvs["k"], wrk_add_dict):
                            # write the source first
                            wrk_add_dict = write_source(kvs, wrk_add_dict)
                            # Append to the list
                            wrk_add_list.append(wrk_add_dict)
                            # Now clear down the dict and
                            # add the new item
                            wrk_add_dict = collections.OrderedDict()
                            wrk_add_dict[kvs["k"]] = kvs["v"]

                    # wrk_add_dict[kvs["k"]] = kvs["v"]
                    print "did we add kvs:", to_json(kvs), " to ", to_json(wrk_add_dict)

                print "Dropping from Non-Comment for kvs:", kvs

            if DBUG:
                do_DBUG("K:", kvs["k"], "V:", kvs["v"],
                        "wrk_ln_head:", wrk_ln_head,
                        "wrk_add_dict:", to_json(wrk_add_dict))

        # increment line counter (wrk_ln)
        wrk_ln += 1
        wrk_ln_head = False
        # reset the Header indicator
        if wrk_ln < len(ln_list) - 1:
            wrk_ln_dict = get_line_dict(ln_list, wrk_ln)
            if is_head(wrk_ln_dict):
                end_segment = True
    # dropping from while loop
    end_ln = wrk_ln - 1

    print "wrk_seg_def:",to_json(ln_control)
    if len(wrk_add_dict) > 0 and ln_control["type"].upper() == "LIST":
        # If we have entries in save_add_dict
        # we need to add wrk_add_dict to save_add_dict
        # then assign save_add_dict to wrk_add_dict
        # and clear down save_add_dict

        if DBUG:
            do_DBUG("wrk_add_dict:", to_json(wrk_add_dict),
                    "len(save_add_dict):", len(save_add_dict),
                    "save_add_dict", to_json(save_add_dict))

        save_add_dict.update(wrk_add_dict)
        wrk_add_dict = save_add_dict

        if DBUG:
            do_DBUG("APPENDED WORK_ADD_DICT",
                    wrk_add_dict)


    if len(save_add_list) > 0:
        # we have entries in save_add_list
        save_add_list.append(wrk_add_dict)
        wrk_add_dict = save_add_list

    if DBUG:
        do_DBUG("returning end_ln:", end_ln,
                "wrk_ln:", wrk_ln,
                "wrk_segment:", wrk_segment,
                "type:", wrk_seg_def,
                "returning dict(wrk_add_dict):", to_json(wrk_add_dict))

    return end_ln, wrk_add_dict, current_segment


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
    # SEG_DEF may define a different level

    # Step 1 is to setup the segment using the start_ln record

    work_ln = strt_ln
    multi = False
    segment = collections.OrderedDict()
    segment_list = []
    sub_segment = collections.OrderedDict()
    list_processing = False
    dict_in_list = False
    end_segment = False

    kvs = {"k": "", "v": "", "source": ""}

    # print "Line_Control:Pre List eval", ln_control
    print "----------------"
    print "Line to Process:",ln_list[strt_ln]
    print "----------------"

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

                elif ln_control["sub_type"] == "list":
                    dict_in_list = False
                    sub_segment = []
                else:
                    dict_in_list = False
                    sub_segment = ""
            list_processing = True
            # print "Dict in List: ", dict_in_list

        else:
            segment = collections.OrderedDict()
            print strt_ln, ":", ln_control["match"]
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
        segment = collections.OrderedDict()

    if key_is_in("level", ln_control):
        match_ln = update_match(ln_control["level"], current_segment,
                                match_ln)

    # Now loop through the lines in the file
    # until we match another SEG_DEF record


    kvs["k"] = ""
    kvs["v"] = ""

    current_line = get_line_dict(ln_list, work_ln)

    if not is_body(current_line):
        # If we are dealing with a header we have already processed it
        # so move to next line
        # print "HEADER"
        work_ln += 1
    else:
        # We are entering a body sub-segment
        print current_line["key"], ":", current_line["type"]

    while not end_segment and (work_ln <= len(ln_list)-1):
        if work_ln == (len(ln_list)-1):
            # We have reached the end of the list
            end_segment = True

        # Get the line to work with
        current_line = get_line_dict(ln_list, work_ln)

        print "------------"
        print "IN WHILE LOOP"
        print "current_line:", current_line
        print "segment: ", segment
        print "list   : ", segment_list
        print "sub-seg: ", sub_segment
        print "------------"


        ttl, val = split_k_v(current_line["line"])
        match_ln = update_match(current_line["level"], ttl, match_ln )
        # print "matching with: ",match_ln

        adj_level = adjusted_level(current_line["level"],match_ln)

        print "Adjusted_Level:", adj_level, " Start_Level", start_lvl

        if adj_level <= start_lvl:
            # We have found the start of the next segment
            k, v = split_k_v(current_line["line"])

            # sub_segment[k] = v
            print "onto next segment"
            print "k:", k, " v:", v
            print len(segment), " Segment:",segment
            print len(sub_segment), " Sub", sub_segment
            print len(segment_list), " list", segment_list
            print "^^^^^^^^^^^^^^^^^"
            end_ln = work_ln - 1
            end_segment = True

        elif adj_level == (start_lvl + 1):
            # We are processing the lines in the segment
            print adj_level, "==", start_lvl + 1
            #print "Do Line:", current_line["key"]

            # we need to check SEG_DEF for instructions
            match_ln = update_match(start_lvl + 1,
                                    headlessCamel(current_line["line"]),
                                    match_ln)
            # print "combined match:", combined_match(start_lvl + 1,
            # match_ln)

            #if find_segment(combined_match(start_lvl + 1, match_ln)):
            #    sub_seg = get_segment(combined_match(start_lvl + 1,
            #                                         match_ln))
            #    print "entering sub process segment"
            #    work_ln, sub_seg, seg_name = process_segment(work_ln,
            #                                                 sub_seg,
            #                                                 match_ln,
            #                                                 start_lvl + 1,
            #                                                 ln_list)
            #    work_ln += 1
            #    segment[seg_name] = sub_seg

            if find_segment(combined_match(start_lvl + 1, match_ln)):
                # we found a combined item that
                # must be drilling down another level
                # work_ln, segment = process_segment(work_ln,
                # get_segment(combined_match(ln_control["level"] + 1,
                # match_ln),
                #                   match_ln, ln_control["level"], ln_list)
                print ">>>>>>>>>>>>>"
                print "ln:", work_ln, "Going Deeper:", \
                    combined_match(ln_control["level"] + 1, match_ln)

                print match_ln
                block_control = get_segment(combined_match(start_lvl + 1,
                                                           match_ln))
                print block_control
                work_ln, sub_seg, seg_name = process_segment(work_ln,
                                                             block_control,
                                                             match_ln,
                                                             start_lvl + 1,
                                                             ln_list)
                print seg_name, ":", sub_seg
                print "<<<<<<<<<<<<<<"
                work_ln += 1
                segment[seg_name] = sub_seg



            else:

                kvs = assign_key_value(current_line["line"],
                                       ln_control,
                                       kvs)
                #print "K:", kvs["k"]," V:", kvs["v"], "Source:",
                # kvs["source"],"]"

                if ("ADDRESSLINE1" in kvs["k"].upper()) or \
                        ("ADDRESSTYPE" in kvs["k"].upper()):

                    kvs["v"], work_ln = build_address(ln_list, work_ln)
                    # print "work_ln = ", work_ln
                    kvs["k"] = "address"

                    print kvs["k"], ":", kvs["v"]

                    # Build an Address Block
                    # By reading the next lines
                    # until we find "ZIP"
                    #return Address dict and work_ln reached

                print "+++++++++++++++++++++++++++"
                print "About to update dict/Lists"
                print kvs["k"], ":", kvs["v"]
                print "segment:", segment
                print "seg_list:", segment_list
                print "sub_seg:", sub_segment
                print "+++++++++++++++++++++++++++"

                if list_processing:
                    if dict_in_list:

                        # print "DICT IN LIST"

                        if kvs["k"] in sub_segment:
                            # this entry exists
                            # so post the current information
                            # reset the segment_list
                            # and append the latest data to a new subset
                            segment_list.append(sub_segment)

                            print segment_list

                            sub_segment = collections.OrderedDict()
                            sub_segment["source"] = kvs["source"]

                        sub_segment[kvs["k"]] = kvs["v"]
                        print "Sub_segment:",sub_segment
                    else:

                        print "Segment List Append:K", kvs["k"], " V:", \
                            kvs["v"]
                        print "sub_type:", ln_control["sub_type"]
                        if ln_control["sub_type"] == "list":
                            segment_list.append(kvs["v"])
                        elif ln_control["sub_type"] == "dict":
                            segment_list.append({kvs["k"]: kvs["v"]})
                            if "source" not in segment_list:

                                print "SETTING source in segment list:", \
                                    kvs["source"]

                            segment_list.append({"source": kvs["source"]})
                        else:
                            segment_list.append(kvs["v"])
                else:

                    # print "NOT LIST PROCESSING"

                    segment[kvs["k"]] = kvs["v"]

                    if "source" not in segment:
                        # print "SETTING source in segment:", current_source

                        segment["source"] = kvs["source"]

        elif adj_level >= (start_lvl + 2):
            print "Down another level"
            # level >= start_level + 2
            # we are going down another level
            seg_def = get_segment(combined_match(start_lvl + 1, match_ln))
            # print "Deal as Sub-segment:"
            # print "process ", current_line["line"]
            # print "seg_def:", seg_def
            work_ln, sub_segment, segment_name = \
                process_segment(work_ln, seg_def, match_ln, start_lvl + 1,
                                                                 ln_list)
            # print "SubSegment:", sub_segment
            segment[segment_name] = sub_segment
            # print "current_segment:", segment[segment_name]
            work_ln += 1

    # If match on SEG_DEF and level is > current level
    # Drill down to another sub-segment


    # else: we have found the start of the next segment
    # So set return values and exit

        work_ln += 1

    print "Segment:", segment

    # finish writing segments
    if list_processing:
        #segment[current_segment] = sub_segment
        # print "segment_list before exit:", segment_list
        # print "segment before exit:", segment
        if len(segment_list) < 1:
            print "Adding sub_segment to segment_list"
            segment_list = [sub_segment]
        else:
            segment_list.append(sub_segment)
        segment = segment_list
        print "Adding segment_list to segment"

        # print "updated segment", segment
        # print "Cur Seg Name:", current_segment
    end_ln = work_ln-2

    if len(segment) < 1:
        print "Adding sub_segment to segment"
        segment = sub_segment

    print "=========================="
    print "End_Line:",end_ln
    print "Current Segment:", current_segment
    # print "Segment:", segment
    # print ""
    # print "segment_list:", segment_list
    # print ""
    # print "Sub_Segment:", sub_segment
    print "=========================="
    return end_ln, segment, current_segment


###############################################################
###############################################################
###############################################################
###############################################################


def adjusted_level(lvl, match_ln):
    # lookup the level based on the max of source line lvl
    # and SEG_DEF matched level

    DBUG = False

    result = lvl
    if find_segment(combined_match(lvl,match_ln)):
        seg_info = get_segment(combined_match(lvl, match_ln))
        if key_is_in("level", seg_info):
            result = max(lvl, seg_info["level"])

    if DBUG:
        do_DBUG("Level(lvl):", lvl, "Result:", result,
                "Using match_ln:", to_json(match_ln))

    return result


def assign_key_value(full_line, wrk_seg_def, kvs):
    # evaluate the line to get key and value

    # print full_line
    line_source = full_line.split(":")
    if len(line_source) > 1:
        kvs["k"] = headlessCamel(line_source[0])
        kvs["v"] = line_source[1].lstrip()
        kvs["v"] = kvs["v"].rstrip()

    else:
        kvs["k"] = "comments"
        kvs["v"] = full_line

    if "SOURCE" in kvs["k"].upper():
        kvs["k"] = headlessCamel(kvs["k"])
        kvs = set_source(kvs)

        # print "SET source:", kvs["source"]

    if (kvs["k"][2] == "/"):
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

    #if key_is_in("dict_name", wrk_seg_def):
    #    if key_is_in("type", wrk_seg_def):
    #        if wrk_seg_def["type"].upper() == "DICT":
    #            kvs["v"] = {kvs["k"]:kvs["v"]}
    #            kvs["k"] = wrk_seg_def["dict_name"]

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
            do_DBUG("Empty city, state, zip: ",len(address_block["city"] +
                    address_block["state"] +
                    address_block["zip"]))

        patch_address = (address_block["addressLine1"] + " " +\
                        address_block["addressLine2"]).rstrip()

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

            if len(patch_address.rstrip()) > len(address_block["addressLine1"]):
                # The zip and state were in Address Line 2
                # so we will update addressLine2
                address_line2 = patch_address[(len(address_block["addressLine1"]) -1):]
                address_line2.lstrip()
                address_line2.rstrip()
                address_block["addressLine2"] = address_line2
            else:
                # the zip and state came from addressLine1
                address_block["addressLine1"] = patch_address.rstrip()

    if DBUG:
        do_DBUG("ADDRESS BLOCK---------",
                to_json(address_block),
                "wk_ln:", wk_ln - 1 )

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
        inspect.stack()[1][2] , "]"
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

    # cycle through the seg dictionary to match against title
    for ky in SEG_DEF:
        if exact == False:
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

    found_line = ln[i]
    extract_line = found_line[i]

    return extract_line


def get_segment(title, exact=False):
    # get the SEG_DEF record using title in Match

    DBUG = False

    result = {}

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


def is_head(ln):
    # Is line type = "HEADER" in ln

    DBUG = False

    result = False

    if key_is_in("type", ln):

        if DBUG:
            do_DBUG("Matching HEAD in:",ln["type"])

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


def key_is(ky,dt,val):
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


def key_is_in(ky,dt):
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
            do_DBUG("lvl:", lvl,"Match_ln", to_json(match_ln),
                    "title:", title, "tmp_seg_def", to_json(tmp_seg_def),
                    "Result:", result)

    return result


def parse_date(d):
    # convert date to json format

    result = ""

    d = d.strip()
    if len(d) > 0:
        # print d
        date_value = datetime.strptime(d, "%m/%d/%Y")
        result = date_value.strftime("%Y%m%d")

    #print result

    return result


def parse_time(t):
    # convert time to  json format

    t = t.strip()
    time_value = datetime.strptime(t, "%m/%d/%Y %I:%M %p")
    # print time_value
    result = time_value.strftime("%Y%m%d%H%M%S+0500")

    # print result
    return result


def segment_prefill(wrk_seg_def, segment_dict):
    # Receive the Segment information for a header line
    # get the seg["pre"] and iterate through the dict
    # assigning to segment_dict
    # First we reset the segment_dict as an OrderedDict

    DBUG = False

    if len(segment_dict)>0:

        print "Prefill- segment_dict:", segment_dict, "NOT EMPTY"

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


def setup_header(ln_ctrl,wrk_ln_dict ):

    DBUG = False

    wrk_add_dict = {}
    segment_name = ln_ctrl["name"]
    returned_segment = ""

    # sub_kvs = {"k": "", "v": "", "source": ""}

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
        #        "Sub_KVS:", sub_kvs,
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

    return k,v


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
    if len(line) >1:
        keym = line[0]

    else:
        keym = txt

    # get the line or the line up to the ":"
    # set the lvl position in the match_ln list
    match_ln[lvl] = keym

    if DBUG:
        do_DBUG("update_match(lvl, txt, match_ln)", lvl, txt, match_ln,
                "keym:", keym, "match_ln["+str(lvl)+"]:", match_ln[lvl])

    return match_ln


def update_save_to(target, src, key):
    # Test the target and update with source

    DBUG = False

    target_type = check_type(target)
    save_to = target

    if DBUG:
        do_DBUG("save_to:", save_to,
                "using source:", src,
                "key:", key,
                "and target:", target,
                "with target_type:", target_type)

    if target_type == "DICT":
        #print save_to[key]
        if check_type(save_to[key]) == "LIST":
            save_to[key] = src[key]
        else:
            save_to[key] = src[key]

    elif target_type == "LIST":
        save_to = src[key]
    elif target_type == "TUPLE":
        save_to[key] = {key:src[key]}
    elif target_type == "STRING":
        string_to_write = src[key]
        save_to = src[key]
    else:
        save_to[key] = src[key]

    if DBUG:
        do_DBUG("returning save_to:", save_to,
                "using source:", src,
                "and target:", target,
                "with target_type:", target_type)

    return save_to


def write_comment(wrk_add_dict, kvs):
    # if value is assigned to comments we need to check
    # if comments already present
    # if so, add to the list

    DBUG = True

    if DBUG:
        do_DBUG("IN WRITE COMMENTS", "wrk_add_dict:",
                to_json(wrk_add_dict), "kvs:", to_json(kvs))

    if not key_is_in(kvs["k"],wrk_add_dict):
        # print kvs["k"]," NOT in wrk_add_dict"
        # so initialize the comments list

        wrk_add_dict[kvs["k"]] = []

    else:
        if isinstance(wrk_add_dict[kvs["k"]], basestring):
            tmp_comment = wrk_add_dict[kvs["k"]]
            print "tmp_comment:",tmp_comment
            # get the comment
            wrk_add_dict[kvs["k"]] = []
            # initialize the list
            wrk_add_dict[kvs["k"]].append(tmp_comment)

    # Now add the comment
    wrk_add_dict[kvs["k"]].append(kvs["v"])

    # kvs["comments"].append(kvs["v"])

    if DBUG:
        do_DBUG("k:", kvs["k"], "v:", kvs["v"],
                "wrk_add_dict["+kvs["k"]+"]:",
                wrk_add_dict[kvs["k"]],
                "wrk_add_dict:", to_json(wrk_add_dict))

    return wrk_add_dict


def write_save_to(save_to, pd):
    # iterate through dict and add to save_to

    """

    :param save_to:
    :param pd:
    :return:
    """
    DBUG = False

    print "pd:", pd

    i = 0
    for item in pd.items():
        key = item[0]
        #print "key:", key
        val = item[1]
        #print "item:", item[1]
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
    if kvs["source"] != "":
        dt["source"] = kvs["source"]

    return dt



