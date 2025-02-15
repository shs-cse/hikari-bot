from os import path
from bot_variables import state
from bot_variables.config import InfoField, TemplateLinks, FileName
from bot_variables.config import EnrolmentSprdsht, MarksSprdsht

from sync_with_servers.sheets import update_student_list, update_marks_sec
from wrappers import jsonc
from wrappers.pygs import pygsheets as pygs
from wrappers.pygs import AuthenticationError, WorksheetNotFound
from wrappers.pygs import update_cells_from_fields, get_google_client
from wrappers.pygs import get_spreadsheet, get_sheet_by_name, copy_spreadsheet
from wrappers.pygs import allow_access, share_with_anyone, share_with_faculty_as_editor
from wrappers.utils import FormatText


def check_google_credentials() -> None:
    if not path.exists(FileName.SHEETS_CREDENTIALS):
        log = f'Sheets credential file "{FileName.SHEETS_CREDENTIALS}" was not found.'
        log += " You will need to log on by clicking on this following link"
        log += " and pasting the code from browser."
        print(FormatText.warning(log))
    try:
        get_google_client()
        print(FormatText.success("Google authorization was successful."))
    except Exception as error:
        log = "Google authorization failed!"
        log += " Did you forget to provide the correct credentials.json file?"
        raise AuthenticationError(FormatText.error(log)) from error


def check_spreadsheet_from_id(spreadsheet_id) -> None:
    get_spreadsheet(spreadsheet_id)


# TODO: done? split into multiple function
def check_enrolment_sheet() -> pygs.Spreadsheet:
    # enrolment id may be empty
    if enrolment_id := state.info[InfoField.ENROLMENT_SHEET_ID]:
        enrolment_sheet = get_spreadsheet(enrolment_id)
    else:
        # enrolment id not found -> create a new sheet
        log = f"Enrolment sheet ID is not specified {FileName.INFO_JSON} file."
        log += " Creating a new spreadsheet..."
        print(FormatText.warning(log))
        spreadsheet_title = EnrolmentSprdsht.TITLE.format(
            course_code=state.info[InfoField.COURSE_CODE], 
            semester=state.info[InfoField.SEMESTER]  # fmt:skip
        )
        enrolment_sheet = copy_spreadsheet(
            template_id=TemplateLinks.ENROLMENT_SHEET,
            title=spreadsheet_title,
            folder_id=state.info[InfoField.MARKS_FOLDER_ID],
        )
    # finally update info file
    jsonc.update_info_field(InfoField.ENROLMENT_SHEET_ID, enrolment_sheet.id)
    # update routines and stuff (for both new and old enrolment sheet)
    update_cells_from_fields(
        enrolment_sheet,
        {
            EnrolmentSprdsht.Meta.TITLE: # fmt:skip
                EnrolmentSprdsht.Meta.FIELDS_TO_CELLS_DICT  # fmt:skip
        },
    )
    allow_access(str(enrolment_sheet.id), state.info[InfoField.ROUTINE_SHEET_ID])
    share_with_anyone(enrolment_sheet)  # also gives it some time to fetch marks groups
    return enrolment_sheet


def check_marks_groups(enrolment_sheet: pygs.Spreadsheet) -> None:
    print(FormatText.wait(f'Fetching "{InfoField.MARKS_GROUPS}" from spreadsheet...'))
    meta_wrksht = get_sheet_by_name(enrolment_sheet, EnrolmentSprdsht.Meta.TITLE)
    marks_groups_cell = EnrolmentSprdsht.Meta.FIELDS_FROM_CELLS_DICT[InfoField.MARKS_GROUPS]
    marks_groups_str: str = meta_wrksht.get_value(marks_groups_cell)
    marks_groups: dict[str, list[int]] = jsonc.loads(marks_groups_str)
    print(FormatText.status(f'"{InfoField.MARKS_GROUPS}": {FormatText.bold(marks_groups)}'))
    # check sections in range
    available_secs = set(range(1, 1 + state.info[InfoField.NUM_SECTIONS]))
    available_secs -= set(state.info[InfoField.MISSING_SECTIONS])
    if available_secs != {sec for group in marks_groups.values() for sec in group}:
        log = "Marks groups contain sections that does not exist in"
        log += f" {meta_wrksht.url}&range={marks_groups_cell}"
        raise ValueError(FormatText.error(log))
    # update info json
    jsonc.update_info_field(InfoField.MARKS_GROUPS, marks_groups)


def check_marks_sheet(sec: int, email: str, group: list[int]) -> None:  # TODO: removed marks_ids as argument. any impact?? # fmt:skip
    marks_ids = state.info[InfoField.MARKS_SHEET_IDS].copy()  # TODO: why copy?
    if marks_ids.get(str(sec), ""):  # key may not exist or value may be ""
        spreadsheet = get_spreadsheet(marks_ids[str(sec)])
    # no spreadsheet in info for the followings
    elif sec == group[0]:  # sec is the first member of the group
        spreadsheet = create_marks_spreadsheet(sec, group, email)
    else:  # first group member has spreadsheet
        spreadsheet = get_spreadsheet(marks_ids[str(group[0])])
    marks_ids[str(sec)] = str(spreadsheet.id)
    jsonc.update_info_field(InfoField.MARKS_SHEET_IDS, marks_ids)
    log = f'Section {sec:02d} > Marks spreadsheet: "{spreadsheet.title}"'
    print(FormatText.success(log))
    sec_sheet = create_marks_worksheet(spreadsheet, sec)
    update_marks_sec(sec_sheet, sec)


def check_marks_groups_and_sheets() -> None:
    if not state.info[InfoField.MARKS_ENABLED]:
        log = "Marks feature is not enabled."
        print(FormatText.status(log))
    else:
        check_marks_groups(state.info[InfoField.ENROLMENT_SHEET_ID])
        for email, marks_group in state.info[InfoField.MARKS_GROUPS].items():
            for section in marks_group:
                check_marks_sheet(section, email, marks_group)


def create_marks_spreadsheet(sec: int, group: list[int], email: str) -> pygs.Spreadsheet:
    print(FormatText.warning(f"Creating new spreadsheet for section {sec:02d}..."))
    spreadsheet = copy_spreadsheet(
        TemplateLinks.MARKS_SHEET,
        MarksSprdsht.TITLE.format(
            course_code=state.info[InfoField.COURSE_CODE],
            sections=",".join(f"{s:02d}" for s in group),
            semester=state.info[InfoField.SEMESTER],
        ),
        state.info[InfoField.MARKS_FOLDER_ID],
    )
    share_with_faculty_as_editor(spreadsheet, email)
    update_cells_from_fields(
        spreadsheet, {MarksSprdsht.Meta.TITLE: MarksSprdsht.Meta.CELL_TO_FILED_DICT}
    )
    return spreadsheet


# create a worksheet for the section marks in spreadsheet
def create_marks_worksheet(spreadsheet: pygs.Spreadsheet, sec: int) -> pygs.Worksheet:
    try:  # success -> sec worksheet already exists
        sec_sheet = get_sheet_by_name(spreadsheet, MarksSprdsht.SecXX.TITLE.format(sec))
    except WorksheetNotFound:
        # fail -> sec worksheet does not exist
        print(FormatText.status("Creating new worksheet..."))
        template_sheet = get_sheet_by_name(spreadsheet, MarksSprdsht.SecXX.TITLE.format(0))
        sec_sheet: pygs.Worksheet = template_sheet.copy_to(spreadsheet.id)  # type:ignore
        sec_sheet.hidden = False
        sec_sheet.title = MarksSprdsht.SecXX.TITLE.format(sec)
        populate_marks_worksheet_with_student_id(sec_sheet, sec)
    return sec_sheet


def populate_marks_worksheet_with_student_id(sec_sheet: pygs.Worksheet, sec: int) -> None:
    start_cell = (MarksSprdsht.SecXX.ACTUAL_ROW_DATA_START, MarksSprdsht.SecXX.COL_FOR_STUDENT_IDS)
    end_cell = (None, MarksSprdsht.SecXX.COL_FOR_STUDENT_IDS)
    student_ids = sec_sheet.get_as_df(start=start_cell, end=end_cell)
    if student_ids.empty and not state.students.empty:  # type:ignore
        is_student_in_sec = state.students[EnrolmentSprdsht.Students.SECTION_COL] == sec
        sec_students = state.students[is_student_in_sec]
        sec_sheet.set_dataframe(
            sec_students[[EnrolmentSprdsht.Students.NAME_COL]], 
            start=start_cell, # fmt:skip
            copy_index=True  # fmt:skip
        )
