import streamlit as st
import requests
import json
import datetime
import traceback
import pandas as pd
import os
import zipfile

points = 20
total_points = 20
deduction = 0.5
expected_success_message = "Transactions have not been implemented yet"


def fields():
    return ['name', 'email', 'address', 'phone', 'ccNumber', 'ccExpiryMonth', 'ccExpiryYear']


def invalid_values():
    return {
        'name': ['Bad', 'A very long name bigger than forty five characters is an invalid name.'],
        'email': ['Bad', 'tom@x.'],
        'address': ['Bad', 'A very long address bigger than forty five characters is an invalid address.'],
        'phone': ['Bad', '123456789', '123456789123456789'],
        'ccNumber': ['123456789012', '12345678901234567'],
        'ccExpiryMonth': [13],
        'ccExpiryYear': [2020, 0]
    }


def valid_values():
    return {
        'name': ['Monica'],
        'email': ['monica@email.com'],
        'address': ['123 Main St'],
        'phone': ['408-555-1212', '408 555 1212', '(408) 555 1212'],
        'ccNumber': ['4444333322221111'],
        'ccExpiryMonth': [7],
        'ccExpiryYear': [2026]
    }


def make_cart(book, quantity=1):
    return {
        "cart": {
            "itemArray": [
                {"book": book, "quantity": quantity}
            ]
        }
    }


def make_customer(form):
    return {"customerForm": form}


def check(condition: bool, message: str, input_json: str = "", points_off: float = deduction, results: list = None) -> bool:
    if not condition:
        case_details = describe_case(message + f" (FAIL, -{points_off})", input_json)
        if results is not None:
            results.append(case_details)
        return False
    return True


def describe_case(title, input_json):
    case_details = f"""
========================================================
{title}
--------------------------------------------------------
{input_json}
========================================================
"""
    return case_details


def submit_order(host_url, form, book, quantity=1):
    headers = {'Content-Type': 'application/json'}
    cart = make_cart(book, quantity)
    customer = make_customer(form)
    payload = {**cart, **customer}
    response = requests.post(f"{host_url}/api/orders", headers=headers, json=payload)
    return response.status_code, response.text, json.dumps(payload, indent=2)


def run_tests(host_url, student_name):
    global points
    points = 20  # Reset points for each student
    results = []
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    try:
        results.append(f"TESTING {student_name} - {host_url}: out of {total_points}\n")
        results.append(
            "===============================================================================\nGRADING NOTES\n===============================================================================\n")
        results.append("""We are testing with the following sections, and each section is worth 4 points.  
 * Missing customer form values - expect a field error
 * Empty customer form values - expect a field error
 * Invalid customer form values - expect a field error
 * Valid customer form values - expect success message
 * Quantity and expiry date logic - expect appropriate errors\n""")

        # Fetch a test book
        book_response = requests.get(f"{host_url}/api/books/1005")
        if book_response.status_code != 200:
            results.append("Failed to fetch a test book.\n")
            return results, 0
        book = book_response.json()

        # Valid form
        form = {
            "name": "Monica",
            "email": "monica@email.com",
            "address": "123 Main St",
            "phone": "408 555 1212",
            "ccNumber": "4444333322221111",
            "ccExpiryMonth": current_month,
            "ccExpiryYear": current_year
        }

        # Run all test cases (similar to the earlier logic)
        # Test for missing fields
        for field in fields():
            test_form = form.copy()
            del test_form[field]
            status, response, payload = submit_order(host_url, test_form, book)
            if status != 400:
                results.append(
                    f"========================================================\nTested with missing field {field}.\nExpected field error but encountered:\n\tstatus_code={status} and \n\tresponse={response}\n\norder placement failed (FAIL, -0.5)\n--------------------------------------------------------\n{payload}\n========================================================\n\n")
                points -= 0.5

        # Test for empty fields
        for field in fields():
            test_form = form.copy()
            test_form[field] = ""
            status, response, payload = submit_order(host_url, test_form, book)
            if status != 400:
                results.append(
                    f"========================================================\nTested with empty value for field {field}.\nExpected field error but encountered:\n\tstatus_code={status} and \n\tresponse={response}\n\norder placement failed (FAIL, -0.5)\n--------------------------------------------------------\n{payload}\n========================================================\n\n")
                points -= 0.5

        # Test for invalid values
        for field, values in invalid_values().items():
            for value in values:
                test_form = form.copy()
                test_form[field] = value
                status, response, payload = submit_order(host_url, test_form, book)
                if status != 400:
                    results.append(
                        f"========================================================\nTested with invalid {field}/{value}.\nExpected field error but encountered:\n\tstatus_code={status} and \n\tresponse={response}\n\norder placement failed (FAIL, -0.25)\n--------------------------------------------------------\n{payload}\n========================================================\n\n")
                    points -= 0.25

        # Valid fields test
        valid_points = 4.0
        for valid_field in fields():
            for valid_value in valid_values()[valid_field]:
                customer_form = form.copy()
                customer_form[valid_field] = valid_value
                status, response, payload = submit_order(host_url, customer_form, book)
                result = check(
                    status == 400 and expected_success_message in response,
                    f"Tested with valid {valid_field}/{valid_value}.\nExpected success message but encountered:\n\tstatus_code={status} and\n\tresponse={response}",
                    payload,
                    0.4,
                    results
                )
                if not result:
                    valid_points -= 0.4
        points -= (4.0 - valid_points)

        # Expiration dates
        last_month_year = current_year if current_month > 1 else current_year - 1
        last_month = current_month - 1 if current_month > 1 else 12

        next_month_year = current_year if current_month < 12 else current_year + 1
        next_month = current_month + 1 if current_month < 12 else 1

        # Reject expiration dates in the past
        customer_form = form.copy()
        customer_form['ccExpiryYear'] = last_month_year
        customer_form['ccExpiryMonth'] = last_month
        status, response, payload = submit_order(host_url, customer_form, book)
        result = check(
            status == 400 and expected_success_message not in response,
            f"Submit with past date {last_month}/{last_month_year}.\nExpected field error but encountered:\n\tstatus_code={status} and\n\tresponse={response}",
            payload,
            1.0, results
        )
        if not result:
            points -= 1.0

        # Accept expiration dates in the current month
        customer_form = form.copy()
        customer_form['ccExpiryYear'] = current_year
        customer_form['ccExpiryMonth'] = current_month
        status, response, payload = submit_order(host_url, customer_form, book)
        result = check(
            status == 400 and expected_success_message in response,
            f"Submit with current date {current_month}/{current_year}.\nExpected success but encountered:\n\tstatus_code={status} and\n\tresponse={response}",
            payload,
            1.0
        )
        if not result:
            points -= 1.0

        # Accept expiration dates in the future month
        customer_form = form.copy()
        customer_form['ccExpiryYear'] = next_month_year
        customer_form['ccExpiryMonth'] = next_month
        status, response, payload = submit_order(host_url, customer_form, book)
        result = check(
            status == 400 and expected_success_message in response,
            f"Submit with future date {next_month}/{next_month_year}.\nExpected success but encountered:\n\tstatus_code={status} and\n\tresponse={response}",
            payload,
            1.0, results
        )
        if not result:
            points -= 1.0

        # Quantity validation
        customer_form = form.copy()
        status, response, payload = submit_order(host_url, customer_form, book, 100)
        result = check(
            status == 400 and expected_success_message not in response,
            f"Submit with invalid quantity (100).\nExpected field error but encountered:\n\tstatus_code={status} and\n\tresponse={response}",
            payload,
            1.0, results
        )
        if not result:
            points -= 1.0

    except Exception as e:
        results.append(f"Error during testing: {traceback.format_exc()}\n")



    # Calculate final score
    results.append(f"Preliminary point total is {points}, subject to rounding.\n")
    final_score = max(0, round(points))
    results.append(f"Your score was rounded from {points} to {final_score} since grades must be integers.\n")
    results.append(f"SCORE for {student_name}: {final_score}/{total_points}\n")
    return results, final_score


def process_csv(file):
    output_dir = "results"
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(file)
    student_scores = []

    with st.spinner("Running tests for all students..."):
        for _, row in df.iterrows():
            student_name = row['StudentName']
            host_url = row['HostURL'].rstrip("/")
            if student_name is None:
                continue

            # Run tests
            results, score = run_tests(host_url, student_name)

            # Save individual results to a file
            result_file = os.path.join(output_dir, f"{student_name}.txt")
            with open(result_file, "w") as f:
                f.writelines(results)

            # Collect score
            student_scores.append({"StudentName": student_name, "Score": score})

        # Create ZIP file
        zip_file = "results.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            for file_name in os.listdir(output_dir):
                zf.write(os.path.join(output_dir, file_name), arcname=file_name)

    return pd.DataFrame(student_scores), zip_file


def main():
    st.title("Bookstore Order Validator")
    # Sample CSV download
    st.subheader("Download Sample CSV")
    sample_data = pd.DataFrame({
        "StudentName": ["Alice", "Bob", "Charlie"],
        "HostURL": ["http://localhost:8080", "http://localhost:8081", "http://localhost:8082"]
    })
    sample_csv = sample_data.to_csv(index=False).encode('utf-8')
    st.download_button("Download Sample CSV", sample_csv, "sample_students.csv", "text/csv")

    # File uploader
    uploaded_file = st.file_uploader("Upload CSV with Student Names and Host URLs", type=["csv"])
    if uploaded_file:
        # Process CSV and generate results
        student_scores, zip_file = process_csv(uploaded_file)

        # Display scores as a table
        st.write("Student Scores")
        st.dataframe(student_scores)

        # Allow downloading the scores as CSV
        csv_data = student_scores.to_csv(index=False).encode('utf-8')
        st.download_button("Download Scores as CSV", csv_data, "scores.csv", "text/csv")

        # Allow downloading the ZIP file of results
        with open(zip_file, "rb") as f:
            st.download_button("Download All Results (ZIP)", f, "results.zip")


if __name__ == "__main__":
    main()
