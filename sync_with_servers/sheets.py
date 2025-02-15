from wrappers.pygs import pygsheets as pygs


def update_student_list(): ...  # TODO: enrolment -> state.students


def update_marks_sec(
    sec_sheet: pygs.Worksheet, sec: int
): ...  # TODO: sec_sheet -> state.students, enrolment
