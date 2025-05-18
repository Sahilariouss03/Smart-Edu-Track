import cv2
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import smtplib
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json

LUXAND_API_KEY = os.getenv("LUXAND_API_KEY")
if not LUXAND_API_KEY:
    raise ValueError("Error: LUXAND_API_KEY environment variable not set. Please set it before running the script.")

LUXAND_API_URL = "https://api.luxand.cloud/photo/search"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "donotreplytomrquiz@gmail.com"
SMTP_PASSWORD = "hwsd xdby pdeq cryi"

QUIZ_LINKS = {
    "Python": "",
    "Math": ""
}

KNOWN_FACES_DIR = "known_faces"
ATTENDANCE_DIR = "attendance_records"
QUIZZES_DIR = "quizzes"
GALLERY_NAME = "students"

last_api_request_time = 0
API_REQUEST_INTERVAL = 5
frame_count = 0

if not os.path.exists(ATTENDANCE_DIR):
    os.makedirs(ATTENDANCE_DIR)
if not os.path.exists(QUIZZES_DIR):
    os.makedirs(QUIZZES_DIR)

course_name = input("Enter the course name for which attendance is being marked (e.g., Python, Math): ").strip()
course_name = re.sub(r'[^a-zA-Z0-9]', '_', course_name)

if course_name not in QUIZ_LINKS:
    raise ValueError(f"Error: Course {course_name} not found in QUIZ_LINKS. Please add the course to QUIZ_LINKS in the script.")

def validate_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M")
    except ValueError:
        raise ValueError("Time must be in HH:MM format (e.g., 10:00)")

print("Enter the class period for this session.")
start_time_str = input("Start time (HH:MM, e.g., 10:00): ").strip()
end_time_str = input("End time (HH:MM, e.g., 11:00): ").strip()

start_time = validate_time(start_time_str)
end_time = validate_time(end_time_str)
if end_time <= start_time:
    raise ValueError("End time must be after start time.")

today_date = datetime.now().date()
start_datetime = datetime.combine(today_date, start_time.time())
end_datetime = datetime.combine(today_date, end_time.time())

current_datetime = datetime.now()
if current_datetime < start_datetime or current_datetime > end_datetime:
    print(f"Current time ({current_datetime.strftime('%H:%M')}) is outside the class period ({start_time_str} to {end_time_str}). Starting monitoring until {end_time_str}.")
else:
    print(f"Starting attendance monitoring for {course_name} from {start_time_str} to {end_time_str}.")

students_file = "students.csv"
if not os.path.exists(students_file):
    raise FileNotFoundError("Error: students.csv not found. Please create a CSV with columns: Course, Name, Email")
students_df = pd.read_csv(students_file)
course_students_df = students_df[students_df["Course"] == course_name]
course_students = course_students_df["Name"].tolist()
if not course_students:
    print(f"Warning: No students found for course {course_name} in students.csv. Attendance will be recorded, but absentees cannot be determined.")

present_students = set()

def get_forms_service():
    SCOPES = ['https://www.googleapis.com/auth/forms.body', 'https://www.googleapis.com/auth/drive']
    CREDENTIALS_FILE = 'credentials.json'
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('forms', 'v1', credentials=creds)

def create_quiz_form(course_name):
    forms_service = get_forms_service()
    form = {
        "info": {
            "title": f"{course_name} Adaptive Quiz",
            "documentTitle": f"{course_name}_Quiz"
        }
    }
    form_result = forms_service.forms().create(body=form).execute()
    form_id = form_result['formId']

    quiz_file = os.path.join(QUIZZES_DIR, f"quizzes_{course_name}.csv")
    if not os.path.exists(quiz_file):
        raise FileNotFoundError(f"Quiz file quizzes_{course_name}.csv not found.")
    
    quiz_df = pd.read_csv(quiz_file)
    medium_quizzes = quiz_df[(quiz_df["Course"] == course_name) & (quiz_df["Difficulty"] == "Medium")]
    if len(medium_quizzes) < 3:
        raise ValueError(f"Not enough medium-difficulty questions for {course_name}. Available: {len(medium_quizzes)}.")
    
    selected_quizzes = medium_quizzes.sample(n=3, random_state=42)

    requests = [
        {
            "updateSettings": {
                "settings": {
                    "quizSettings": {
                        "isQuiz": True
                    }
                },
                "updateMask": "quizSettings.isQuiz"
            }
        },
        {
            "updateFormInfo": {
                "info": {
                    "description": f"Adaptive quiz for {course_name} to cover missed topics."
                },
                "updateMask": "description"
            }
        }
    ]

    for idx, row in selected_quizzes.iterrows():
        question = {
            "createItem": {
                "item": {
                    "title": row['Question'],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [
                                    {"value": row['Option1']},
                                    {"value": row['Option2']},
                                    {"value": row['Option3']},
                                    {"value": row['Option4']}
                                ]
                            },
                            "grading": {
                                "pointValue": 1,
                                "correctAnswers": {
                                    "answers": [{"value": row[f'Option{row["CorrectAnswer"]}']}]
                                }
                            }
                        }
                    }
                },
                "location": {"index": idx}
            }
        }
        requests.append(question)

    forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    form_response = forms_service.forms().get(formId=form_id).execute()
    form_url = form_response.get('responderUri', f"https://docs.google.com/forms/d/{form_id}/edit")
    return form_url

if not QUIZ_LINKS[course_name]:
    print(f"Creating Google Form for {course_name} quiz...")
    QUIZ_LINKS[course_name] = create_quiz_form(course_name)
    print(f"Created Google Form for {course_name}: {QUIZ_LINKS[course_name]}")

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

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.endswith((".jpg", ".jpeg", ".png")):
        student_name = os.path.splitext(filename)[0].replace("_", " ")
        image_path = os.path.join(KNOWN_FACES_DIR, filename)
        register_student(image_path, student_name)

today = datetime.now().strftime("%d_%m_%Y")
csv_file = os.path.join(ATTENDANCE_DIR, f"attendance_{course_name}_{today}.csv")

if not os.path.exists(csv_file):
    attendance_df = pd.DataFrame(columns=["Course", "Name", "Date", "Time"])
    attendance_df.to_csv(csv_file, index=False)
else:
    attendance_df = pd.read_csv(csv_file)

webcam_index = 1
cap = cv2.VideoCapture(webcam_index)
if not cap.isOpened():
    print(f"Error: Could not open webcam at index {webcam_index}. Ensure the external webcam is connected and not in use by another application.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print(f"Using external webcam at index {webcam_index}. Starting attendance monitoring system for {course_name}. Press 'q' to quit.")

while True:
    current_datetime = datetime.now()
    if current_datetime > end_datetime:
        print(f"Class period ({start_time_str} to {end_time_str}) has ended. Stopping attendance monitoring.")
        break

    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame from webcam. Check if the webcam is connected and working.")
        break

    frame = cv2.resize(frame, (1280, 960))

    height, width, _ = frame.shape
    cv2.putText(frame, f"Frame: {width}x{height}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    detection_region = (int(width*0.3), int(height*0.2), int(width*0.4), int(height*0.6))
    x, y, w, h = detection_region
    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
    cv2.putText(frame, "Place face here", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    current_time = time.time()
    if current_time - last_api_request_time >= API_REQUEST_INTERVAL:
        print("Processing frame for recognition...")
        temp_image_path = "temp.jpg"
        cv2.imwrite(temp_image_path, frame)

        if frame_count < 3:
            cv2.imwrite(f"debug_frame_{frame_count}.jpg", frame)
            print(f"Saved debug frame as debug_frame_{frame_count}.jpg")
            frame_count += 1

        with open(temp_image_path, "rb") as image_file:
            files = {"photo": image_file}
            headers = {"token": LUXAND_API_KEY}
            params = {"gallery": GALLERY_NAME}
            response = requests.post(LUXAND_API_URL, headers=headers, files=files, params=params)
        
        last_api_request_time = current_time

        if response.status_code == 200:
            result = response.json()
            print(f"Recognition response: {result} - Headers: {response.headers}")
            if result and isinstance(result, list) and len(result) > 0:
                recognized_name = result[0].get("name", "Unknown")
                probability = result[0].get("probability", 0)

                if probability > 0.5:
                    cv2.putText(frame, f"Detected: {recognized_name} ({probability:.2f})", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    present_students.add(recognized_name)

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

        os.remove(temp_image_path)

    cv2.imshow("Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

if course_students:
    absent_students = [student for student in course_students if student not in present_students]
    print("\nAbsent Students:")
    if absent_students:
        for student in absent_students:
            student_email = course_students_df[course_students_df["Name"] == student]["Email"].iloc[0]
            absence_subject = f"Absence Alert: {course_name} Class on {today}"
            absence_body = f"Dear {student},\n\nYou were absent for the {course_name} class on {today}. To cover the missed topics, please complete the adaptive quiz linked below.\n\nBest regards,\nAttendance System"
            send_email(student_email, absence_subject, absence_body)

            quiz_link = QUIZ_LINKS[course_name]
            quiz_subject = f"Adaptive Quiz for {course_name} Class on {today}"
            quiz_body = f"Dear {student},\n\nYou missed the {course_name} class on {today}. Please complete the following adaptive quiz to cover the topics you missed:\n\n{quiz_link}\n\nSubmit your answers by the end of the week.\n\nBest regards,\nAttendance System"
            send_email(student_email, quiz_subject, quiz_body)
    else:
        print("All enrolled students were present.")

cap.release()
cv2.destroyAllWindows()
print("Attendance monitoring system stopped.")