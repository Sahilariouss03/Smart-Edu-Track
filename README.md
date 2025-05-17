# Student Attendance Monitoring System

This project uses Luxand.cloud API to recognize faces via a webcam and mark attendance in a CSV file.

Student Attendance Monitoring System
This project implements a student attendance monitoring system using facial recognition. It leverages the Luxand.cloud API to recognize students via a webcam, marks their attendance in a course-specific CSV file, identifies absent students for a given class period, sends them an email alert, and provides an adaptive quiz to cover missed topics. The quiz results are recorded in a separate CSV file.
Features

Facial Recognition: Uses Luxand.cloud API to detect and recognize students via an external webcam.
Attendance Tracking: Records attendance for each student in a CSV file named by course and date (e.g., attendance_Python_18_05_2025.csv).
Class Period Monitoring: Allows the user to specify a class period (start and end time) for attendance monitoring.
Absentee Alerts: Identifies absent students and sends email alerts using an SMTP server.
Adaptive Quiz: Provides a medium-difficulty quiz for absent students with questions specific to the course, and records their answers in a separate CSV (e.g., quiz_results_Python_18_05_2025.csv).

Project Structure
StudentAttendanceSystem/
├── known_faces/
│   ├── Sahil.jpg
│   └── ...
├── attendance_records/
│   ├── attendance_Python_18_05_2025.csv
│   ├── quiz_results_Python_18_05_2025.csv
│   └── ...
├── quizzes/
│   ├── quizzes_Python.csv
│   ├── quizzes_Math.csv
│   └── ...
├── students.csv
├── attendance_system.py
└── README.md


known_faces/: Contains images of students for facial recognition, named as their full name (e.g., Sahil.jpg).
attendance_records/: Stores attendance CSVs (attendance_{course}_{date}.csv) and quiz results (quiz_results_{course}_{date}.csv).
quizzes/: Stores quiz questions for each course (e.g., quizzes_Python.csv).
students.csv: Lists enrolled students with their course and email.
attendance_system.py: The main script for attendance monitoring.

Dependencies
To run this project locally, you need the following dependencies:

Python 3.11 or later
Required Python packages:
opencv-python: For webcam video capture and frame processing.
requests: For making API calls to Luxand.cloud.
pandas: For handling CSV files.


A Luxand.cloud API key (sign up at Luxand.cloud).
An SMTP server account for sending email alerts (e.g., Gmail with an app password).
An external webcam (set to index 1 in the script).

Setup Instructions
1. Clone the Repository
Clone this repository to your local machine:
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name

2. Create and Activate a Virtual Environment
Set up a Python virtual environment to manage dependencies:
python -m venv .venv

Activate the virtual environment:

On Windows:.venv\Scripts\activate


On Unix/Linux/Mac:source .venv/bin/activate



3. Install Dependencies
Install the required Python packages:
pip install opencv-python requests pandas

4. Set Up Luxand.cloud API Key
The script uses an environment variable to securely store your Luxand.cloud API key:

Sign up at Luxand.cloud and get your API key.
Set the API key as an environment variable:
On Windows (PowerShell):$env:LUXAND_API_KEY = "your_api_key_here"


On Unix/Linux/Mac:export LUXAND_API_KEY=your_api_key_here


To make it permanent, add it to your system environment variables:
On Windows: Control Panel > System > Advanced system settings > Environment Variables > New (under User variables).
Variable name: LUXAND_API_KEY
Variable value: your_api_key_here





5. Configure SMTP for Email Alerts
The script sends email alerts to absent students using an SMTP server:

Update the SMTP settings in attendance_system.py with your email credentials:SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"


For Gmail:
Enable 2-Step Verification in your Google Account.
Go to Security > App passwords > Generate a new app password.
Use this app password as SMTP_PASSWORD (not your regular Gmail password).


Replace with your SMTP server details if using a different provider (e.g., Outlook, Yahoo).

6. Prepare Required Files
Create the following files in the project directory:
students.csv
List all enrolled students with their course and email:
Course,Name,Email
Python,Sahil,sahil@example.com
Python,John,john@example.com
Math,Alice,alice@example.com

known_faces Directory

Place student images in the known_faces folder, named as their full name (e.g., Sahil.jpg).
Ensure the name matches exactly with the Name column in students.csv.

quizzes Directory
Create a quiz file for each course, e.g., quizzes_Python.csv:
Course,Question,Option1,Option2,Option3,Option4,CorrectAnswer,Difficulty
Python,What is a list in Python?,A function,A data type,A loop,A variable,2,Medium
Python,How do you define a function?,def func():,function func():,define func():,func def():,1,Medium
Python,What does len() do?,Loops a list,Returns length,Prints a string,Defines a variable,2,Medium

Steps to Run Locally

Ensure the Webcam Is Connected:

The script uses an external webcam at index 1. Ensure your external webcam is plugged in and recognized by your system.
If your webcam index is different, modify webcam_index = 1 in the script to the correct index.


Run the Script:

Start the script:python attendance_system.py




Enter Course and Class Period:

When prompted, enter the course name (e.g., Python).
Enter the class period start time (e.g., 10:00) and end time (e.g., 11:00) in HH:MM format.
The script will monitor attendance during this period.


Mark Attendance:

Position your face within the yellow rectangle in the video feed.
If recognized (e.g., Sahil), the script will mark attendance in attendance_records/attendance_Python_18_05_2025.csv.


End the Session:

Press q to stop the script, or wait until the class period ends.
The script will identify absent students (e.g., John), send email alerts, and present a quiz for each absent student.


Quiz for Absent Students:

For each absent student, the script loads 3 medium-difficulty questions from quizzes/quizzes_{course_name}.csv.
The quiz is presented on-screen, and the student (simulated by you) answers by entering 1-4.
Answers are recorded in attendance_records/quiz_results_{course_name}_{today}.csv.



Steps Involved in the Process

Setup:

The script loads enrolled students and their email IDs from students.csv.
It registers faces from the known_faces folder with Luxand.cloud.


Attendance Monitoring:

During the user-specified class period, the script captures webcam frames every 5 seconds.
Frames are sent to Luxand.cloud for facial recognition.
Recognized students are marked as present in a course-specific CSV.


Identify Absentees:

At the end of the session, the script compares present students against the enrolled list to identify absentees.


Send Alerts:

For each absent student, an email alert is sent using the configured SMTP server.
The email includes the course name and date of absence.


Adaptive Quiz:

For each absent student, the script loads 3 medium-difficulty questions from the course’s quiz file.
The quiz is presented on-screen, and answers are recorded in a separate CSV.
Results are printed (e.g., “John’s score: 2/3”).



Example Output
Enter the course name for which attendance is being marked (e.g., Python, Math): Python
Enter the class period for this session.
Start time (HH:MM, e.g., 10:00): 03:00
End time (HH:MM, e.g., 11:00): 03:10
Using external webcam at index 1. Starting attendance monitoring system for Python. Press 'q' to quit.
Processing frame for recognition...
Attendance marked for Sahil in Python at 03:01:00
...
Class period (03:00 to 03:10) has ended. Stopping attendance monitoring.

Absent Students:
Alert: John was absent for Python on 18_05_2025.
Email alert sent to john@example.com for John.

Adaptive Quiz for John (Course: Python)
Question 1: What is a list in Python?
1. A function
2. A data type
3. A loop
4. A variable
Enter your answer (1-4): 2
Correct!
...
Quiz completed! John's score: 2/3
Attendance monitoring system stopped.

Notes

Time Zone: The script uses your system’s local time (e.g., IST). Ensure your system clock is correct.
Email Setup: Replace the SMTP credentials in the script with your actual email and app password. For Gmail, use an app password (not your regular password).
Naming Consistency: Ensure student names in known_faces (e.g., Sahil.jpg) match exactly with names in students.csv (e.g., Sahil).
GitHub: The script is safe for GitHub (API key is hidden). Use the .gitignore file to exclude sensitive data:.venv/
attendance_records/
debug_frame_*.jpg
temp.jpg



Troubleshooting

**Web

