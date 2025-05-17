import cv2
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import random
import smtplib
from email.mime.text import MIMEText

# Luxand.cloud API settings
# Set your Luxand API key as an environment variable named LUXAND_API_KEY
# On Windows, use: set LUXAND_API_KEY=your_api_key_here
# On Unix/Linux/Mac, use: export LUXAND_API_KEY=your_api_key_here
LUXAND_API_KEY = os.getenv("LUXAND_API_KEY")
if not LUXAND_API_KEY:
    raise ValueError("Error: LUXAND_API_KEY environment variable not set. Please set it before running the script.")

LUXAND_API_URL = "https://api.luxand.cloud/photo/search"

# SMTP settings for sending email alerts (replace with your details)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "donotreplytomrquiz@gmail.com" 
SMTP_PASSWORD = "hwsd xdby pdeq cryi"  # Replace with your app password (not regular password)

# Paths and gallery settings
KNOWN_FACES_DIR = "known_faces"
ATTENDANCE_DIR = "attendance_records"
QUIZZES_DIR = "quizzes"  # Directory for quiz files
GALLERY_NAME = "students"  # Define a gallery for registered faces

# API request throttling settings
last_api_request_time = 0
API_REQUEST_INTERVAL = 5  # Seconds between API requests
frame_count = 0  # For saving a few frames for debugging

# Ensure directories exist
if not os.path.exists(ATTENDANCE_DIR):
    os.makedirs(ATTENDANCE_DIR)
if not os.path.exists(QUIZZES_DIR):
    os.makedirs(QUIZZES_DIR)

# Prompt user for the current course name
course_name = input("Enter the course name for which attendance is being marked (e.g., Python, Math): ").strip()
# Sanitize course name for use in filename (replace spaces with underscores, remove special characters)
course_name = re.sub(r'[^a-zA-Z0-9]', '_', course_name)

# Prompt user for class period
def validate_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M")
    except ValueError:
        raise ValueError("Time must be in HH:MM format (e.g., 10:00)")

print("Enter the class period for this session.")
start_time_str = input("Start time (HH:MM, e.g., 10:00): ").strip()
end_time_str = input("End time (HH:MM, e.g., 11:00): ").strip()

# Validate and parse times
start_time = validate_time(start_time_str)
end_time = validate_time(end_time_str)
if end_time <= start_time:
    raise ValueError("End time must be after start time.")

# Set the date to today
today_date = datetime.now().date()
start_datetime = datetime.combine(today_date, start_time.time())
end_datetime = datetime.combine(today_date, end_time.time())

# Check if the current time is within the class period
current_datetime = datetime.now()
if current_datetime < start_datetime or current_datetime > end_datetime:
    print(f"Current time ({current_datetime.strftime('%H:%M')}) is outside the class period ({start_time_str} to {end_time_str}). Starting monitoring until {end_time_str}.")
else:
    print(f"Starting attendance monitoring for {course_name} from {start_time_str} to {end_time_str}.")

# Load enrolled students from students.csv
students_file = "students.csv"
if not os.path.exists(students_file):
    raise FileNotFoundError("Error: students.csv not found. Please create a CSV with columns: Course, Name, Email")
students_df = pd.read_csv(students_file)
# Filter students for the current course
course_students_df = students_df[students_df["Course"] == course_name]
course_students = course_students_df["Name"].tolist()
if not course_students:
    print(f"Warning: No students found for course {course_name} in students.csv. Attendance will be recorded, but absentees cannot be determined.")

# Keep track of students present during this session
present_students = set()

# Function to register a student with Luxand.cloud
def register_student(image_path, student_name):
    with open(image_path, "rb") as image_file:
        files = {"photo": image_file}
        headers = {"token": LUXAND_API_KEY}
        data = {"name": student_name, "gallery": GALLERY_NAME}
        response = requests.post("https://api.luxand.cloud/photo", headers=headers, data=data, files=files)
        if response.status_code == 200:
            print(f"Registered {student_name} with Luxand.cloud. Response: {response.json()}")
        else:
            print(f"Failed to register {student_name}: {response.status_code} - {response.text} - Headers: {response.headers}")

# Function to send email alert
def send_email_alert(to_email, student_name, course_name, date):
    msg = MIMEText(f"Dear {student_name},\n\nYou were absent for the {course_name} class on {date}. Please complete the adaptive quiz provided to cover the missed topics.\n\nBest regards,\nAttendance System")
    msg["Subject"] = f"Absence Alert: {course_name} Class on {date}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"Email alert sent to {to_email} for {student_name}.")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

# Register all students from known_faces folder
for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.endswith((".jpg", ".jpeg", ".png")):
        student_name = os.path.splitext(filename)[0].replace("_", " ")
        image_path = os.path.join(KNOWN_FACES_DIR, filename)
        register_student(image_path, student_name)

# Get today's date for the attendance file
today = datetime.now().strftime("%d_%m_%Y")
# Create CSV filename with course name and date
csv_file = os.path.join(ATTENDANCE_DIR, f"attendance_{course_name}_{today}.csv")
quiz_results_file = os.path.join(ATTENDANCE_DIR, f"quiz_results_{course_name}_{today}.csv")

# Initialize or load the attendance CSV
if not os.path.exists(csv_file):
    attendance_df = pd.DataFrame(columns=["Course", "Name", "Date", "Time"])
    attendance_df.to_csv(csv_file, index=False)
else:
    attendance_df = pd.read_csv(csv_file)

# Initialize the quiz results CSV
if not os.path.exists(quiz_results_file):
    quiz_results_df = pd.DataFrame(columns=["Course", "Student", "Date", "Question", "StudentAnswer", "CorrectAnswer", "Result"])
    quiz_results_df.to_csv(quiz_results_file, index=False)
else:
    quiz_results_df = pd.read_csv(quiz_results_file)

# Initialize video capture with the external webcam (index 1)
webcam_index = 1  # Use the external webcam
cap = cv2.VideoCapture(webcam_index)
if not cap.isOpened():
    print(f"Error: Could not open webcam at index {webcam_index}. Ensure the external webcam is connected and not in use by another application.")
    exit()

# Set webcam resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print(f"Using external webcam at index {webcam_index}. Starting attendance monitoring system for {course_name}. Press 'q' to quit.")

while True:
    # Check if the current time is within the class period
    current_datetime = datetime.now()
    if current_datetime > end_datetime:
        print(f"Class period ({start_time_str} to {end_time_str}) has ended. Stopping attendance monitoring.")
        break

    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame from webcam. Check if the webcam is connected and working.")
        break

    # Resize frame to a higher resolution for better API compatibility
    frame = cv2.resize(frame, (1280, 960))

    # Add debug overlay for frame dimensions
    height, width, _ = frame.shape
    cv2.putText(frame, f"Frame: {width}x{height}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Draw a detection region (approximate area where face should be)
    detection_region = (int(width*0.3), int(height*0.2), int(width*0.4), int(height*0.6))
    x, y, w, h = detection_region
    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
    cv2.putText(frame, "Place face here", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # Check if enough time has passed since the last API request
    current_time = time.time()
    if current_time - last_api_request_time >= API_REQUEST_INTERVAL:
        print("Processing frame for recognition...")
        # Save the frame temporarily to send to the API
        temp_image_path = "temp.jpg"
        cv2.imwrite(temp_image_path, frame)

        # Save a few frames for debugging (first 3 frames)
        if frame_count < 3:
            cv2.imwrite(f"debug_frame_{frame_count}.jpg", frame)
            print(f"Saved debug frame as debug_frame_{frame_count}.jpg")
            frame_count += 1

        # Send the frame to Luxand.cloud for recognition
        with open(temp_image_path, "rb") as image_file:
            files = {"photo": image_file}
            headers = {"token": LUXAND_API_KEY}
            params = {"gallery": GALLERY_NAME}
            response = requests.post(LUXAND_API_URL, headers=headers, files=files, params=params)
        
        last_api_request_time = current_time  # Update the last request time

        if response.status_code == 200:
            result = response.json()
            print(f"Recognition response: {result} - Headers: {response.headers}")
            if result and isinstance(result, list) and len(result) > 0:
                # Get the name of the recognized student (highest confidence)
                recognized_name = result[0].get("name", "Unknown")
                probability = result[0].get("probability", 0)

                # Display the name on the frame if probability is high enough
                if probability > 0.5:
                    cv2.putText(frame, f"Detected: {recognized_name} ({probability:.2f})", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    # Add to present students
                    present_students.add(recognized_name)

                    # Mark attendance if the person is recognized and not already marked today
                    print(f"Recognized name: {recognized_name}, CSV entries: {attendance_df['Name'].values}")
                    already_marked = recognized_name in attendance_df["Name"].values
                    if not already_marked:
                        now = datetime.now()
                        date_str = now.strftime("%d-%m-%Y")
                        time_str = now.strftime("%H:%M:%S")
                        new_entry = pd.DataFrame([[course_name, recognized_name, date_str, time_str]], columns=["Course", "Name", "Date", "Time"])
                        attendance_df = pd.concat([attendance_df, new_entry], ignore_index=True)
                        attendance_df.to_csv(csv_file, index=False)
                        print(f"Attendance marked for {recognized_name} in {course_name} at {time_str}")
                    else:
                        print(f"Attendance already marked for {recognized_name} in {course_name} today.")
                else:
                    cv2.putText(frame, f"Unknown (Probability: {probability:.2f})", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                print(f"No face detected in frame by Luxand.cloud. Response: {result}")
                cv2.putText(frame, "No face detected (Luxand)", (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            print(f"API request failed: {response.status_code} - {response.text} - Headers: {response.headers}")
            cv2.putText(frame, "API Error", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Remove the temporary file
        os.remove(temp_image_path)

    # Display the frame
    cv2.imshow("Attendance System", frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Identify absent students
if course_students:
    absent_students = [student for student in course_students if student not in present_students]
    print("\nAbsent Students:")
    if absent_students:
        for student in absent_students:
            # Send email alert
            student_email = course_students_df[course_students_df["Name"] == student]["Email"].iloc[0]
            send_email_alert(student_email, student, course_name, today)

            # Load quiz questions for the course
            quiz_file = os.path.join(QUIZZES_DIR, f"quizzes_{course_name}.csv")
            if not os.path.exists(quiz_file):
                print(f"Warning: Quiz file quizzes_{course_name}.csv not found. Cannot provide quiz for {student}.")
                continue

            quiz_df = pd.read_csv(quiz_file)
            # Select medium-difficulty questions
            medium_quizzes = quiz_df[(quiz_df["Course"] == course_name) & (quiz_df["Difficulty"] == "Medium")]
            if len(medium_quizzes) < 3:
                print(f"Warning: Not enough medium-difficulty questions for {course_name}. Available: {len(medium_quizzes)}.")
                continue

            # Randomly select 3 questions
            selected_quizzes = medium_quizzes.sample(n=3, random_state=42)

            # Present the quiz to the student (simulated on-screen)
            print(f"\nAdaptive Quiz for {student} (Course: {course_name})")
            print("Please answer the following questions to cover the missed topics:")
            score = 0
            quiz_entries = []
            for idx, row in selected_quizzes.iterrows():
                print(f"\nQuestion {idx + 1}: {row['Question']}")
                print(f"1. {row['Option1']}")
                print(f"2. {row['Option2']}")
                print(f"3. {row['Option3']}")
                print(f"4. {row['Option4']}")
                answer = input("Enter your answer (1-4): ").strip()
                correct_answer = str(row['CorrectAnswer'])
                result = "Correct" if answer == correct_answer else "Incorrect"
                if answer == correct_answer:
                    print("Correct!")
                    score += 1
                else:
                    print(f"Incorrect. The correct answer is: {row[f'Option{correct_answer}']}")
                # Record the answer
                quiz_entry = pd.DataFrame([[course_name, student, today, row['Question'], answer, correct_answer, result]],
                                          columns=["Course", "Student", "Date", "Question", "StudentAnswer", "CorrectAnswer", "Result"])
                quiz_entries.append(quiz_entry)
            print(f"\nQuiz completed! {student}'s score: {score}/3")
            # Save quiz results to CSV
            quiz_results_df = pd.concat([quiz_results_df] + quiz_entries, ignore_index=True)
            quiz_results_df.to_csv(quiz_results_file, index=False)
    else:
        print("All enrolled students were present.")

# Release resources
cap.release()
cv2.destroyAllWindows()
print("Attendance monitoring system stopped.")