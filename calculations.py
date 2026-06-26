"""
calculations.py
Core logic for SGPA, CGPA, and target CGPA planning.
Grading scale used: 10-point scale (standard in most Indian universities).
O=10, A+=9, A=8, B+=7, B=6, C=5, F=0
You can adjust GRADE_POINTS below to match your institution's scale.
"""

GRADE_POINTS = {
    "O": 10,
    "A+": 9,
    "A": 8,
    "B+": 7,
    "B": 6,
    "C": 5,
    "F": 0,
}


def calculate_sgpa(subjects):
    """
    subjects: list of dicts -> [{"credits": 4, "grade_point": 9}, ...]
    Returns SGPA rounded to 2 decimal places.
    """
    total_credits = sum(s["credits"] for s in subjects)
    if total_credits == 0:
        return 0.0
    weighted_sum = sum(s["credits"] * s["grade_point"] for s in subjects)
    return round(weighted_sum / total_credits, 2)


def calculate_cgpa(semesters):
    """
    semesters: list of dicts -> [{"sgpa": 8.5, "total_credits": 24}, ...]
    CGPA = sum(SGPA_i * credits_i) / sum(credits_i)
    Returns CGPA rounded to 2 decimal places.
    """
    total_credits = sum(s["total_credits"] for s in semesters)
    if total_credits == 0:
        return 0.0
    weighted_sum = sum(s["sgpa"] * s["total_credits"] for s in semesters)
    return round(weighted_sum / total_credits, 2)


def calculate_required_sgpa(current_cgpa, completed_credits, target_cgpa,
                             remaining_semesters, credits_per_semester):
    """
    Calculates the average SGPA needed in remaining semesters to hit target CGPA.

    current_cgpa: CGPA so far
    completed_credits: total credits earned so far
    target_cgpa: the CGPA the student wants to achieve
    remaining_semesters: number of semesters left
    credits_per_semester: average/expected credits per remaining semester

    Returns dict with required SGPA and whether it's achievable (max 10).
    """
    remaining_credits = remaining_semesters * credits_per_semester
    total_credits = completed_credits + remaining_credits

    if total_credits == 0 or remaining_credits == 0:
        return {"required_sgpa": None, "achievable": False,
                "message": "Not enough data to calculate."}

    required_total_points = (target_cgpa * total_credits) - (current_cgpa * completed_credits)
    required_sgpa = round(required_total_points / remaining_credits, 2)

    if required_sgpa <= 0:
        return {
            "required_sgpa": 0,
            "achievable": True,
            "message": "You have already secured this target CGPA! 🎉"
        }
    elif required_sgpa > 10:
        return {
            "required_sgpa": required_sgpa,
            "achievable": False,
            "message": "This target is not mathematically achievable (required SGPA exceeds 10)."
        }
    else:
        return {
            "required_sgpa": required_sgpa,
            "achievable": True,
            "message": f"You need an average SGPA of {required_sgpa} in your remaining semesters."
        }
