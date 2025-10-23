# ui/helptext.py
class HELP:
    """Central place to edit dashboard help copy."""

    DEFAULT = "Default"

    # KPI tooltips
    KPI_STUDENTS = DEFAULT
    KPI_AVG_GRADE = DEFAULT
    KPI_MEDIAN_LETTER = DEFAULT
    KPI_ECHO_ENGAGEMENT = DEFAULT
    KPI_FS = DEFAULT
    KPI_ASSIGNMENT_AVG = DEFAULT

    # Echo tables
    ECHO_SUMMARY_COLUMNS = {
        "Media Title": DEFAULT,
        "Video Duration": DEFAULT,
        "# of Unique Viewers": DEFAULT,
        "Average View %": DEFAULT,
        "% of Students Viewing": DEFAULT,
        "% of Video Viewed Overall": DEFAULT,
    }

    ECHO_MODULE_COLUMNS = {
        "Module": DEFAULT,
        "Average View %": DEFAULT,
        "# of Students Viewing": DEFAULT,
        "Overall View %": DEFAULT,
        "# of Students": DEFAULT,
    }

    # Gradebook tables
    GRADEBOOK_SUMMARY_DEFAULT = DEFAULT  # assignment columns are dynamic → use a fallback
    GRADEBOOK_MODULE_COLUMNS = {
        "Module": DEFAULT,
        "Avg % Turned In": DEFAULT,
        "Avg Average Excluding Zeros": DEFAULT,
        "n_assignments": DEFAULT,
    }

    # Charts
    CHART_ECHO = DEFAULT
    CHART_GB = DEFAULT
