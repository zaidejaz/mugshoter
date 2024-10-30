def get_prompt(record):
    prompt = f"""
                    Generate arrest records for {record.countyOfBooking}, using the following structure and rules. Understand that the county name may change for each record, and this will impact the county-specific hashtags and details.
Names should be in the format Last Name, First Name Middle Initial (if available), followed by the Arrest Date in the format MM/DD/YYYY HH
First Name: {record.firstName}
Last Name: {record.lastName}
DateofBooking: {record.dateOfBooking}
offenseDescription: {record.offenseDescription}
Each offense should be listed on a new line and should start with /.
Do not alter the shorthand text provided for offenses; retain the exact format without changes.
Do not duplicate any charges. List each charge only once.
At the bottom, if a bond amount is available, include it as a sum. If no bond amount is provided, leave it off.
Hashtags should follow the structure:
#[CountyName]
#[CountyName]Mugshots
#[FirstNameLastName] (with no spaces between the first and last names).
Do not split the first and last names in the hashtags.
If no bond amount is provided, do not display a placeholder.
If the county name is different (e.g., Pulaski, Jefferson, etc.), adjust the county name and hashtags accordingly.
Example Output Format:

EDWARDS, JOHN M
Arrest Date: 08/24/2024 00:34
Offenses:
/ OPER MTR VEHICLE U/INFUL ALC/ SUBS (189A.010(1E)-2ND (AGG CIR) MISDEMEANOR
/ WANTON ENDANGERMENT - 2ND DEGREE MISDEMEANOR
/ DRUG PARAPHERNALIA - BUY/POSSESS 218A.500(2) MISDEMEANOR
/ OPERATING ON SUSPENDED OR REVOKED OPERATORS LICENSE MISDEMEANOR
/ OPERATING MOTOR VEHICLE U/INFLUENCE ALC/DRUGS/ETC .08 - 1ST OFF MISDEMEANOR
/ ATTEMPTED POSS CONT SUB 1ST DEG 1ST OFF (HEROIN) FELONY
/ PROMOTING CONTRABAND- FENTANYL, CARFENTANIL, OR DERIVATIVE OTHER
/ POSS CONT SUB 1ST DEG 1ST OFF (DRUG UNSPECIFIED) FELONY
/ TRAFF IN CONT SUB, 1ST OFFENSE(CARFENTANIL OR FENTANIL) FELONY

Bond Amount: $25,000.00

#JeffersonCounty #JeffersonCountyMugshots #JohnEdwards

Additional Notes:

For multiple charges, offenses should be separated by new lines, and each charge should start with a /.
Remove any placeholder if the bond amount isn't available.
Maintain the hashtag format for county and name, with the county name adaptable based on the data provided.                
"""  # Customize as needed
    return prompt