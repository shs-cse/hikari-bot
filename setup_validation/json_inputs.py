import re, os
from bot_variables import state
from bot_variables.config import FileName, RegexPattern, InfoField
from wrappers.jsonc import read_json, update_json, update_info_field
from wrappers.utils import FormatText
from setup_validation.google_sheets import check_google_credentials, check_spreadsheet_from_id
from setup_validation.google_sheets import check_enrolment_sheet, check_marks_groups_and_sheets


# match state.info with the valid json file to skip checking all the fields
def has_info_passed_before() -> bool:
    if not os.path.exists(FileName.VALID_JSON):
        return False
    passed = read_json(FileName.VALID_JSON)
    # matches all values with previously passed json (except buttons)
    if all(state.info[key] == passed[key] for key in state.info):
        print(FormatText.success("Check complete! Matches previously passed valid json."))
        update_json(state.info, FileName.VALID_JSON)  # update valid json file
        return True
    else:
        # mismatch -> needs checking each field
        print(FormatText.warning("Needs checking every json input field..."))
        os.remove(FileName.VALID_JSON)
        return False


# check and load the json
def check_and_load_info() -> None:
    check_google_credentials()
    state.info = read_json(FileName.INFO_JSON)
    if not has_info_passed_before():
        check_info_fields()
        check_regex_patterns()
        check_sections(state.info[InfoField.NUM_SECTIONS], state.info[InfoField.MISSING_SECTIONS])
        check_marks_enabled()
        check_spreadsheet_from_id(state.info[InfoField.ROUTINE_SHEET_ID])
        check_enrolment_sheet()
        check_marks_groups_and_sheets()
        # create valid json file
        update_json(state.info, FileName.VALID_JSON)
    # TODO: pull data from sec marksheets, update df_marks_section (and update df_marks costly?)


# check if info file contains all the fields
def check_info_fields() -> None:
    for attr, field in vars(InfoField).items():
        # skip private variables/attributes
        if attr.startswith("_"):
            continue
        # check if every fieldname exists in info
        if not field in state.info:
            log = f'{FileName.INFO_JSON} file does not contain the field: "{field}".'
            raise KeyError(FormatText.error(log))
    # passed all field checks
    log = f"{FileName.INFO_JSON} file contains all the necessary field keys."
    print(FormatText.success(log))


# check if info details matches proper regex
def check_regex_patterns() -> None:
    fields_and_patterns = {
        InfoField.COURSE_CODE: RegexPattern.COURSE_CODE,
        InfoField.COURSE_NAME: RegexPattern.COURSE_NAME,
        InfoField.SEMESTER: RegexPattern.SEMESTER,
        InfoField.ROUTINE_SHEET_ID: RegexPattern.GOOGLE_DRIVE_LINK_ID,
        InfoField.ST_SHEET_ID: RegexPattern.GOOGLE_DRIVE_LINK_ID,
        InfoField.MARKS_FOLDER_ID: RegexPattern.GOOGLE_DRIVE_LINK_ID,
        InfoField.GUILD_ID: RegexPattern.DISCORD_ID,
        InfoField.BOT_TOKEN: RegexPattern.DISCORD_BOT_TOKEN,
    }
    # check each of the fields in a loop
    for field, pattern in fields_and_patterns.items():
        log = f'{FileName.INFO_JSON} > "{field}": '
        extracted = re.search(pattern, state.info[field])
        if not extracted:
            log += rf'"{state.info[field]}" does not match expected pattern: "{pattern}".'
            raise ValueError(FormatText.error(log))
        # update if not exact match (e.g full link -> id only)
        update_info_field(field, extracted[0])
        log += FormatText.bold(extracted[0])
        print(FormatText.status(log))
    # validated all regex checks
    log = f"Course details regex checks out in {FileName.INFO_JSON} file."
    print(FormatText.success(log))


# check number of sections and missing sections
def check_sections(num_sec: int, missing_secs: list[int]) -> None:
    # make sure positive
    if num_sec <= 0:
        log = "Number of sections must be positive"
        raise ValueError(FormatText.error(log))
    # check missing sections
    if missing_secs:
        if 1 in missing_secs:
            log = "Section 1 is used as template, can't be a missing section."
            raise ValueError(FormatText.error(log))
        if not set(missing_secs).issubset(range(1, num_sec)):
            log = "Missing sections that don't exist."
            log += " Keep in mind, the last section cannot be missing."
            log += " Reduce number of sections instead."
            raise ValueError(FormatText.error(log))
    # passed all checks
    log = "Number of sections and missing sections seems ok."
    print(FormatText.success(log))


# check if marks_enabled has boolean values or not
def check_marks_enabled() -> None:
    if not isinstance(state.info[InfoField.MARKS_ENABLED], bool):
        log = "Marks enabled must be a boolean value"
        raise TypeError(FormatText.error(log))
    # validated marks enabled
    log = "enabled" if state.info[InfoField.MARKS_ENABLED] else "disabled"
    print(FormatText.success(f"Marks spreadsheets are {log} for all sections."))
