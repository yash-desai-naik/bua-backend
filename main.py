from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import tempfile
import math


app = FastAPI()

# cors
origins = [
    "http://localhost:5173",
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
    manager_band_text = employee_mapping_df[employee_mapping_df["Emp ID"] == manager_id]["Current Band Equivalence"].values
    reportee_band_text = employee_mapping_df[employee_mapping_df["AA Emp. Code"] == reportee_parent_id]["Current Band Equivalence"].values

    if manager_band_text.size == 1 and reportee_band_text.size == 1:
        manager_band_numeric = calculate_band_numeric(manager_band_text[0], band_range)
        reportee_band_numeric = calculate_band_numeric(reportee_band_text[0], band_range)

        if manager_band_numeric >= 0 and reportee_band_numeric >= 0:
            if abs(manager_band_numeric - reportee_band_numeric) >= 3:
                 return "High Step Gap"
            elif manager_band_numeric == reportee_band_numeric:
                return "Low Step Gap"

    return "Other Step Gap"

def checkParentId(parentId, unique_jobs):
    print(unique_jobs)

    check = False
    ids = unique_jobs["Emp ID"].tolist()
    print(f' ids: {ids}')
    if parentId in ids:
        check = True
    return parentId if check else None


@app.post("/api/process_excel")
async def process_excel_file(specific_value: str, excel_file: UploadFile = File(...)):
    # final_response = {}
    # Create a temporary file to store the uploaded Excel file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await excel_file.read())
        temp_file.close()

        # Read the Excel file into separate dataframes
        df_band_range = pd.read_excel(temp_file.name, sheet_name="Band Range")
        df_employee_mapping = pd.read_excel(temp_file.name, sheet_name="Employee Mapping")

    # # Filter the "BU" column of the "Employee Mapping" sheet based on the specific value
    # filtered_employee_mapping = df_employee_mapping[df_employee_mapping["BU"] == specific_value]

    print(f'specific_value: {specific_value}')
    if specific_value == "null" or specific_value=="":
        specific_value = None  # Convert "null" to None

    # Check if specific_value is provided for filtering
    if specific_value is not None:
        print('ing')
        # Filter the "BU" column of the "Employee Mapping" sheet based on the specific value
        filtered_employee_mapping = df_employee_mapping[df_employee_mapping["BU"] == specific_value]
    else:
        # If specific_value is not provided, use the entire Employee Mapping data
        filtered_employee_mapping = df_employee_mapping


    # Create an empty list to store the JSON response
    json_response = []

    # Define the dynamic band range based on your data
    dynamic_band_range = df_band_range["Band"].unique().tolist()
    print(f" dynamic_band_range: {dynamic_band_range}")


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
                id = job_row["Emp ID"]
                parentId = job_row["AA Emp. Code"]
                unique_job = {
                    "title": job_row["Unique Job"],
                    "current_band": job_row["Current Band Equivalence"],
                    "current_grade": job_row["Current Grade"],
                    "hayScore": job_row["Hay Score"],
                    "outlierIcon": calculate_outlier_icon(job_row["Current Band Equivalence"], band, job_row["Hay Score"]),                    
                    "stepGapIcon": calculate_step_gap_icon(id, parentId, df_employee_mapping,dynamic_band_range),
                    "id": id,            # Include "Emp ID" as id
                    "parentId": checkParentId(parentId, filtered_employee_mapping)
               }

                band_dict["uniqueJobs"].append(unique_job)
        # Add the band dictionary to the JSON response
        json_response.append(band_dict)
        # final_response["unique_bu_list"] = unique_bu_list
        # final_response["data"] = json_response

    return json_response




