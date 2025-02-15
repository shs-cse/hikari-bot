import pygsheets.exceptions
import requests, pygsheets, re
import pandas as pd
import pygsheets.client
from pygsheets.exceptions import *  # type:ignore
from bot_variables.config import RegexPattern
from wrappers.utils import FormatText
from bot_variables.config import FileName
from bot_variables import state


# folder id -> link
def get_link_from_folder_id(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"


# sheet id -> link
def get_link_from_sheet_id(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


# destination sheet id + source sheet id -> allow access link
def get_allow_access_link_from_sheet_id(dest_sheet_id: str, src_sheet_id: str) -> str:
    dest_worksheet_url = get_link_from_sheet_id(dest_sheet_id)
    return f"{dest_worksheet_url}/externaldata/addimportrangepermissions?donorDocId={src_sheet_id}"


# link -> sheets/folder id
def get_drive_id_from_link(link: str) -> str | None:
    if matched := re.search(RegexPattern.GOOGLE_DRIVE_LINK_ID, link):
        return matched.group()


# authorization
def get_google_client() -> pygsheets.client.Client:
    return pygsheets.authorize(client_secret=FileName.GOOGLE_CREDENTIALS)


# get a spreadsheet object
def get_spreadsheet(spreadsheet_id: str) -> pygsheets.Spreadsheet:
    print(FormatText.wait("Fetching spreadsheet..."))
    url = get_link_from_sheet_id(spreadsheet_id)
    log = f"Url: {FormatText.bold(url)}"
    print(FormatText.status(log))
    google_client = get_google_client()
    try:
        spreadsheet = google_client.open_by_key(spreadsheet_id)
        log = FormatText.bold(spreadsheet.title)
        print(FormatText.success(f'Fetched "{log}" spreadsheet successfully.'))
    except Exception as error:
        log = "Could not access this sheet. Is this link correct?"
        log += " And accessible with your GSUITE accout?\n"
        log += get_link_from_sheet_id(spreadsheet_id)
        raise SpreadsheetNotFound(FormatText.error(log)) from error
    # warn if file is trashed
    drive_api_files = google_client.drive.service.files()
    trashed_response = drive_api_files.get(fileId=spreadsheet_id, fields="trashed").execute()
    trashed = trashed_response["trashed"]
    if trashed:
        print(FormatText.warning("Fetched spreadsheet is in google drive trash!!"))
    return spreadsheet


# get a specific worksheet (tab) by name from a spreadsheet
def get_sheet_by_name(  # TODO: rename worksheet
    spreadsheet_obj_or_id: pygsheets.Spreadsheet | str, 
    worksheet_name: str  # fmt:skip
) -> pygsheets.Worksheet:
    if isinstance(spreadsheet_obj_or_id, pygsheets.Spreadsheet):
        spreadsheet = spreadsheet_obj_or_id
    else:
        spreadsheet = get_spreadsheet(spreadsheet_obj_or_id)
    print(FormatText.status(f"Worksheet/Tab Name: {FormatText.bold(worksheet_name)}"))
    try:
        worksheet = spreadsheet.worksheet_by_title(worksheet_name)
        print(FormatText.status(f"Worksheet/Tab Url: {FormatText.bold(worksheet.url)}"))
        return worksheet
    except Exception as error:
        log = FormatText.error(f"Could not find sheet named '{worksheet_name}'!")
        raise WorksheetNotFound(log) from error


# get complete sheet data as pandas dataframe
def get_sheet_data(  # TODO: rename worksheet
    spreadsheet_obj_or_id: pygsheets.Spreadsheet | str, 
    worksheet_title: str  # fmt:skip
) -> pd.DataFrame | bool:
    worksheet = get_sheet_by_name(spreadsheet_obj_or_id, worksheet_title)
    return worksheet.get_as_df()


# share spreadsheet publicly
def share_with_anyone(spreadsheet: pygsheets.Spreadsheet) -> None:
    print(FormatText.wait("Sharing spreadsheet publicly..."))
    print(FormatText.status(f"Url: {FormatText.bold(spreadsheet.url)}"))
    spreadsheet.share("", role="reader", type="anyone")


def share_with_faculty_as_editor(
    spreadsheet: pygsheets.Spreadsheet, # fmt:skip
    faculty_email: str  # fmt:skip
) -> None:
    print(FormatText.wait(f"Sharing spreadsheet with {FormatText.bold(faculty_email)}..."))
    print(FormatText.status(f"Url: {FormatText.bold(spreadsheet.url)}"))
    if re.search(RegexPattern.EMAIL_ADDRESS, faculty_email):
        # spreadsheet.share(faculty_email, role='owner', transferOwnership=True)
        spreadsheet.share(faculty_email, role="writer", type="user")
        log = f"Spreadsheet shared with email: {FormatText.bold(faculty_email)}"
        print(FormatText.success(log))
    else:
        log = f"Email {FormatText.bold(faculty_email)} is not in proper format."
        print(FormatText.error(log))


# copy from a template spreadsheet and return a spreadsheet object
def copy_spreadsheet(template_id: str, title: str, folder_id: str) -> pygsheets.Spreadsheet:
    status_logs = [
        f"Template: {FormatText.bold(get_link_from_sheet_id(template_id))}",
        f"Spreadsheet Title: {FormatText.bold(title)}",
        f"Drive Folder: {FormatText.bold(get_link_from_folder_id(folder_id))}",
        f"Creating the new spreadsheet...",
    ]
    print(FormatText.wait("Copying spreadsheet from a template..."))
    for log in status_logs:
        print(FormatText.status(log))
    spreadsheet = get_google_client().create(title=title, template=template_id, folder=folder_id)
    # finally return newly copied spreadsheet
    log = f"Done copying: {FormatText.bold(get_link_from_sheet_id(str(spreadsheet.id)))}"
    print(FormatText.status(log))
    return spreadsheet


# update cell values from dictionary in a sheet
def update_sheet_values(
    cell_value_dict: dict,
    worksheet: pygsheets.Worksheet | None = None,
    *,
    spreadsheet_id: str | None = None,
    worksheet_title: str | None = None,
) -> None:
    ranges = list(cell_value_dict.keys())
    # pygsheet require the values to be a list of list, i.e., matrix
    values = [val if type(val) is list else [[val]] for val in cell_value_dict.values()]
    # edit sheet with set_values
    if not worksheet:
        if not spreadsheet_id or not worksheet_title:
            log = "Neither Spreadsheet id nor Worksheet was provided"
            raise SpreadsheetNotFound(FormatText.error(log))
        worksheet = get_sheet_by_name(spreadsheet_id, worksheet_title)
    print(FormatText.wait(f"Editing spreadsheet cells..."))
    print(FormatText.status(f"Worksheet name: {FormatText.bold(worksheet.title)}"))
    print(FormatText.status(f"Url: {FormatText.bold(worksheet.url)}"))
    if len(str(cell_value_dict)) <= 100:
        print(FormatText.status(f"Setting cell values: {FormatText.bold(cell_value_dict)}"))
    else:
        print(FormatText.status(f"Setting range values: {FormatText.bold(cell_value_dict.keys())}"))
    worksheet.update_values_batch(ranges, values)


# directly update cells, no need to check
def update_cells_from_fields(
    spreadsheet: pygsheets.Spreadsheet, 
    sheet_cell_fields_dict: dict  # fmt:skip
) -> None:
    for sheet_name, cell_field_dict in sheet_cell_fields_dict.items():
        worksheet = spreadsheet.worksheet_by_title(sheet_name)
        # map info field to their actual values for updating sheets
        cell_value_dict = {}
        for cell, field in cell_field_dict.items():
            value = state.info[field]
            if isinstance(value, list):
                value = ",".join(str(item) for item in value)
            cell_value_dict[cell] = value
        update_sheet_values(cell_value_dict, worksheet)


# allow access shenanigans
def allow_access(dest_spreadsheet_id: str, src_spreadsheet_id: str) -> None:
    print(FormatText.wait("Allowing sheet access..."))
    log = f"Pull from: {FormatText.bold(get_link_from_sheet_id(src_spreadsheet_id))}"
    print(FormatText.status(log))
    log = f"Push to: {FormatText.bold(get_link_from_sheet_id(dest_spreadsheet_id))}"
    print(FormatText.status(log))
    token = get_google_client().oauth.token
    url = get_allow_access_link_from_sheet_id(dest_spreadsheet_id, src_spreadsheet_id)
    requests.post(url, headers={"Authorization": f"Bearer {token}"})
