# ui/helptext.py
class HELP:
    # KPIs
    STUDENTS = "Active StudentEnrollment count from Canvas (excludes concluded/withdrawn)."
    MEDIAN_LETTER = "Middle letter grade after ordering A+…F. Robust to outliers."
    AVG_ASSIGN_GRADE = "Class average of 'Average Excluding Zeros' across assignments."

    # Echo tables
    ECHO_AVG_VIEW = "Mean of per-media (view_seconds / duration) for videos in the module."
    ECHO_OVERALL = "Sum(view_seconds) / (duration * #students), then averaged across media."
    ECHO_STUDENTS_VIEWING = "Average unique viewers per video in the module (not a sum)."

    # Gradebook tables
    GB_TURNED_IN = "Average of '% Turned In' across assignments in the module."
    GB_AVG_EXCL0 = "Average of 'Average Excluding Zeros' across assignments in the module."

    # Charts
    CHART_ECHO = (
        "Bars: total students with the filled portion = # of unique viewers per module. "
        "Lines: Avg View % and Overall View % on a percent axis."
    )
    CHART_GB = (
        "Two lines: Avg %% Turned In and Avg Excluding Zeros per module (0–100%)."
    )
