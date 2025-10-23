# ui/helptext.py
class HELP:
    """Central place to edit dashboard help copy."""

    DEFAULT = "Default"

    # KPI tooltips
    KPI_STUDENTS = # of enrolled students
    KPI_AVG_GRADE = Average Final Grade Score
    KPI_MEDIAN_LETTER = Median Letter Grade
    KPI_ECHO_ENGAGEMENT = Average % of video watched for students who click play
    KPI_FS = # of Fs
    KPI_ASSIGNMENT_AVG = Average Assignment Grade %

    # Echo tables
    ECHO_SUMMARY_COLUMNS = {
        "Media Title": Video Title,
        "Video Duration": Video Length,
        "# of Unique Viewers": # of Students who clicked play,
        "Average View %": % of video viewed by students who clicked play,
        "% of Students Viewing": % of total students who clicked play,
        "% of Video Viewed Overall": Total amount of video watched as a % of available video by the class as a whole,
    }

    ECHO_MODULE_COLUMNS = {
        "Module": Module Title,
        "Average View %": Average % of video watched by students who clicked play per module,
        "# of Students Viewing": Average # of students who clicked play per module,
        "Overall View %": Average % of available video watched per module by the class as a whole,
        "# of Students": # of students in the course,
    }

    # Gradebook tables
    GRADEBOOK_SUMMARY_DEFAULT = DEFAULT  # assignment columns are dynamic → use a fallback
    GRADEBOOK_MODULE_COLUMNS = {
        "Module": Module Title,
        "Avg % Turned In": The % of assignments being turned in per module,
        "Avg Average Excluding Zeros": Average assignment grade excluding missing assignments per module,
        "n_assignments": # of assignments per module,
    }

    # Charts
    CHART_ECHO = DEFAULT
    CHART_GB = DEFAULT
