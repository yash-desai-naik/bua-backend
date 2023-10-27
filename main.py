from fastapi import FastAPI, UploadFile, File
import pandas as pd
import tempfile
import math

app = FastAPI()

def calculate_outlier_icon(current_band_equivalence, band, hay_score):
    if current_band_equivalence < band:
        return -1  # Negative outlier
    elif current_band_equivalence > band:
        return 1  # Positive outlier
    else:
        return 0  # No outlier

@app.post("/api/process_excel")
async def process_excel_file(specific_value: str, excel_file: UploadFile = File(...)):
    # Create a temporary file to store the uploaded Excel file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await excel_file.read())
        temp_file.close()

        # Read the Excel file into separate dataframes
        df_band_range = pd.read_excel(temp_file.name, sheet_name="Band Range")
        df_employee_mapping = pd.read_excel(temp_file.name, sheet_name="Employee Mapping")

    # Filter the "BU" column of the "Employee Mapping" sheet based on the specific value
    filtered_employee_mapping = df_employee_mapping[df_employee_mapping["BU"] == specific_value]

    # Create an empty list to store the JSON response
    json_response = []

    # Iterate over each band in the "Band Range" sheet
    for index, row in df_band_range.iterrows():
        band = row["Band"]
        min_range = row["Min"]
        max_range = row["Max"]

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

        # Create a dictionary for the band and unique jobs
        band_dict = {"band": band, 
                     "range":f'{row["Min"]}-{row["Max"]}',
                     "uniqueJobs": []
                     }

        # Check if there are any unique jobs in the band's range
        if not unique_jobs.empty:
            # Iterate over each unique job and add it to the band's unique jobs list
            for _, job_row in unique_jobs.iterrows():
                unique_job = {
                    "title": job_row["Unique Job"],
                    "current_band": job_row["Current Band Equivalence"],
                    "hayScore": job_row["Hay Score"],
                    "outlierIcon": calculate_outlier_icon(job_row["Current Band Equivalence"], band, job_row["Hay Score"])
                }

                band_dict["uniqueJobs"].append(unique_job)

        # Add the band dictionary to the JSON response
        json_response.append(band_dict)

    return json_response
