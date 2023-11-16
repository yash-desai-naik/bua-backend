from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import tempfile
import math
import random
import colorsys
import pandas as pd
import numpy as np


app = FastAPI()

# cors
origins = [
    "http://localhost:5173",
    "https://bua-nu.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_outlier_icon(current_band_equivalence, band, hay_score):
    if current_band_equivalence < band:
        return -1  # Negative outlier
    elif current_band_equivalence > band:
        return 1  # Positive outlier
    else:
        return 0  # No outlier


def calculate_band_numeric(band_text, band_range):
    band_index = band_range.index(band_text) if band_text in band_range else -1
    return band_index


def calculate_step_gap_icon(manager_id, reportee_parent_id, employee_mapping_df, band_range):
    manager_band_text = employee_mapping_df[employee_mapping_df["Emp ID"]
                                            == manager_id]["Current Band Equivalence"].values
    reportee_band_text = employee_mapping_df[employee_mapping_df["AA Emp. Code"]
                                             == reportee_parent_id]["Current Band Equivalence"].values

    if manager_band_text.size == 1 and reportee_band_text.size == 1:
        manager_band_numeric = calculate_band_numeric(
            manager_band_text[0], band_range)
        reportee_band_numeric = calculate_band_numeric(
            reportee_band_text[0], band_range)

        if manager_band_numeric >= 0 and reportee_band_numeric >= 0:
            if abs(manager_band_numeric - reportee_band_numeric) >= 3:
                return "High Step Gap"
            elif manager_band_numeric == reportee_band_numeric:
                return "Low Step Gap"

    return "Other Step Gap"


def checkParentId(parentId, unique_jobs):

    check = False
    ids = unique_jobs["Emp ID"].tolist()
    if parentId in ids:
        check = True
    return parentId if check else None


def extract_numbers(range_str):
    if range_str.startswith('--'):
        return f"{range_str[2:]} and below"
    elif range_str.endswith('--'):
        return f"{range_str[:-2]} and above"
    else:
        min_val, max_val = range_str.split('-')
        return f"{min_val}-{max_val}"

 # Dictionary to store generated colors for each unique current_grade
current_grade_colors = {}


def get_or_generate_color(current_grade):
    """Get the color for a given current_grade or generate a new one."""
    if current_grade not in current_grade_colors:
        # Generate a random color for the current_grade
        hue = random.random()
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.8)
        current_grade_colors[current_grade] = tuple(
            int(val * 255) for val in rgb)
    color_list = current_grade_colors[current_grade]

    # return as rgb string

    return f"rgb({color_list[0]}, {color_list[1]}, {color_list[2]})"


@app.post("/api/process_excel")
async def process_excel_file(
    bu_filter: (str | None) = Query(None, alias="bu_filter"),
    job_family_mapping: (str | None) = Query(None, alias="job_family_mapping"),
    excel_file: UploadFile = File(...),
):
    # Create a temporary file to store the uploaded Excel file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await excel_file.read())
        temp_file.close()

        # Read the Excel file into separate dataframes
        df_band_range = pd.read_excel(temp_file.name, sheet_name="Band Range")
        df_employee_mapping = pd.read_excel(
            temp_file.name, sheet_name="Employee Mapping")

    print(f"bu_filter: {bu_filter}")
    print(f"job_family_mapping: {job_family_mapping}")

    print(bu_filter is not None or job_family_mapping is not None)
    print(bu_filter is not None or job_family_mapping is not None)
    filtered_employee_mapping = df_employee_mapping
    # Check if bu_filter is provided for filtering
    if bu_filter is not None or job_family_mapping is not None:
        # Filter the "BU" column of the "Employee Mapping" sheet based on bu_filter

        # Apply filter based on bu_filter if provided
        if bu_filter is not None:
            filtered_employee_mapping = filtered_employee_mapping[
                filtered_employee_mapping["BU"] == bu_filter
            ]

        # Apply additional filter based on "Job Family/ Function mapping" if provided
        if job_family_mapping is not None:
            filtered_employee_mapping = filtered_employee_mapping[
                filtered_employee_mapping[
                    "Job Family/ Function mapping (as per finalised list)"] == job_family_mapping
            ]

    print(filtered_employee_mapping)

    # Check for NaN values
    nan_check = filtered_employee_mapping.isna().any()

    # Check for infinity values
    inf_check = (filtered_employee_mapping ==
                 np.inf).any() | (filtered_employee_mapping == -np.inf).any()

    # Print columns with NaN values
    print("Columns with NaN values:")
    print(nan_check[nan_check].index.tolist())

    # Print columns with infinity values
    print("Columns with Infinity values:")
    print(inf_check[inf_check].index.tolist())

    filtered_employee_mapping['Current Grade'].fillna('Unknown', inplace=True)
    filtered_employee_mapping['Designation'].fillna('Unknown', inplace=True)

    # Create an empty list to store the JSON response
    json_response = []

    # Define the dynamic band range based on your data
    dynamic_band_range = df_band_range["Band"].unique().tolist()

    # Iterate over each band in the "Band Range" sheet
    for index, row in df_band_range.iterrows():
        band = row["Band"]
        min_range = row["Min"]
        max_range = row["Max"]

        percentage = f'{math.ceil((row["Percentage"]*100))}%' if row["Percentage"] != "-" else None

        # Handle infinity values in the "Max" column
        if max_range == "-":
            max_range = math.inf
        else:
            max_range = float(max_range)

        # Handle negative infinity values in the "Min" column
        if min_range == "-":
            min_range = -math.inf
        else:
            min_range = float(min_range)

        # Filter the unique jobs in the filtered employee mapping based on the Hay Score range
        unique_jobs = filtered_employee_mapping[
            (filtered_employee_mapping["Hay Score"] >= min_range) &
            (filtered_employee_mapping["Hay Score"] <= max_range)
        ]

        range = f'{row["Min"]}-{row["Max"]}'
        formatted_range = extract_numbers(range)

        # Create a dictionary for the band and unique jobs
        band_dict = {"band": band,
                     "range": formatted_range,
                     "percentage": percentage,
                     "uniqueJobs": []
                     }

        # Check if there are any unique jobs in the band's range
        if not unique_jobs.empty:
            # Iterate over each unique job and add it to the band's unique jobs list
            for _, job_row in unique_jobs.iterrows():
                id = job_row["Emp ID"]
                parentId = job_row["AA Emp. Code"]

                # Get or generate a color for the current_grade
                current_grade_color = get_or_generate_color(
                    job_row["Current Band Equivalence"])

                unique_job = {
                    "title": job_row["Unique Job"],
                    "current_band": job_row["Current Band Equivalence"],
                    "current_grade": job_row["Current Grade"],
                    "current_grade_color": current_grade_color,
                    "sub_job_family": job_row["Sub Job Family"],
                    "hayScore": job_row["Hay Score"],
                    "outlierIcon": calculate_outlier_icon(job_row["Current Band Equivalence"], band, job_row["Hay Score"]),
                    "stepGapIcon": calculate_step_gap_icon(id, parentId, df_employee_mapping, dynamic_band_range),
                    "id": id,            # Include "Emp ID" as id
                    "parentId": checkParentId(parentId, filtered_employee_mapping)
                }

                band_dict["uniqueJobs"].append(unique_job)
        # Add the band dictionary to the JSON response
        json_response.append(band_dict)
        # final_response["unique_bu_list"] = unique_bu_list
        # final_response["data"] = json_response

    current_grade_color = {}
    return json_response
