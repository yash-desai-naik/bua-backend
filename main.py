import json
import pandas as pd

# Load the Excel file into pandas dataframes
employee_mapping = pd.read_excel('Emp data.xlsx', sheet_name='Employee Mapping')
job_evaluation_data = pd.read_excel('Emp data.xlsx', sheet_name='Job Evaluation Data')
band_range = pd.read_excel('Emp data.xlsx', sheet_name='Band Range')

# Filter rows where the 'BU' column matches a specific value (e.g., 'YourSpecificBUValue')
specific_value = 'BU-A'
employee_mapping = employee_mapping[employee_mapping['BU'] == specific_value]

# Create a mapping of "Unique Job" to "Proposed band" from 'Job Evaluation Data'
job_mapping = dict(zip(job_evaluation_data['Unique Job'], job_evaluation_data['Proposed band']))

# Define a function to convert band strings to numeric values
def convert_band_to_numeric(band_string):
    if band_string is not None:
        numeric_part = ''.join(filter(str.isdigit, band_string))
        if numeric_part:
            return int(numeric_part)
    return 0  # Return 0 if the input is None or if no numeric part is found

# Define a function to calculate outliers
def calculate_outlier(row):
    current_band = convert_band_to_numeric(row['Current Band Equivalence'])
    proposed_band = convert_band_to_numeric(job_mapping.get(row['Unique Job'], None))
    if current_band is not None and proposed_band is not None:
        if current_band > proposed_band:
            return -1 # negative outlier
        elif current_band < proposed_band:
            return 1 # positive outlie
    return 0 # no outlier

# Apply the function to each row in the 'Employee Mapping' dataframe
employee_mapping['Outlier'] = employee_mapping.apply(calculate_outlier, axis=1)

# Create a dictionary to store the results in the desired JSON format
results = []

# Merge 'Band Range' data with 'employee_mapping' to get 'hayScoreRange'
employee_mapping = employee_mapping.merge(band_range[['Band', 'Min', 'Max']], left_on='Current Band Equivalence', right_on='Band', how='left')

# Group the data by 'band' and 'hayScoreRange'
grouped = employee_mapping.groupby(['Current Band Equivalence', 'Min', 'Max'])


for (band, min_range, max_range), group in grouped:
    unique_jobs = []
    for index, row in group.iterrows():
        title = row['Unique Job']
        outlier_icon = row['Outlier']
        hay_score = row['Hay Score']
        
        unique_job_data = {
            "title": title,
            "outlierIcon": outlier_icon,
            "hayScore": hay_score
        }
        
        unique_jobs.append(unique_job_data)
    
    # Calculate the percentage based on the range's "Min" and "Max" values
    percentage = 15 #dummy

    result_dict = {
        "band": band,
        "hayScoreRange": f"{min_range}-{max_range}",
        "percentage": percentage, #dummy
        "uniqueJobs": unique_jobs
    }

    results.append(result_dict)

# Save the results to a JSON file
with open('output_data.json', 'w') as json_file:
    json.dump(results, json_file, indent=4)
