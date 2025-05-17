import cv2
import requests
import os
import pandas as pd
from datetime import datetime
import time
import re

# Luxand.cloud API settings
# Set your Luxand API key as an environment variable named LUXAND_API_KEY
# On Windows, use: set LUXAND_API_KEY=your_api_key_here
# On Unix/Linux/Mac, use: export LUXAND_API_KEY=your_api_key_here
LUXAND_API_KEY = os.getenv("LUXAND_API_KEY")
if not LUXAND_API_KEY:
    raise ValueError("Error: LUXAND_API_KEY environment variable not set. Please set it before running the script.")

LUXAND_API_URL = "https://api.luxand.cloud/photo/search"

# Paths and gallery settings
KNOWN_FACES_DIR = "known_faces"
ATTENDANCE_DIR = "attendance_records"
GALLERY_NAME = "students"  # Define a gallery for registered faces

# API request throttling settings
last_api_request_time = 0
API_REQUEST_INTERVAL = 5  # Seconds between API requests
frame_count = 0  # For saving a few frames for debugging

# Ensure attendance directory exists
if not os.path.exists(ATTENDANCE_DIR):
    os.makedirs(ATTENDANCE_DIR)

# Prompt user for the current course name
course_name = input("Enter the course name for which attendance is being marked (e.g., Python, Math): ").strip()
# Sanitize course name for use in filename (replace spaces with underscores, remove special characters)
course_name = re.sub(r'[^a-zA-Z0-9]', '_', course_name)

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

# Initialize or load the attendance CSV
if not os.path.exists(csv_file):
    attendance_df = pd.DataFrame(columns=["Course", "Name", "Date", "Time"])
    attendance_df.to_csv(csv_file, index=False)
else:
    attendance_df = pd.read_csv(csv_file)

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

# Release resources
cap.release()
cv2.destroyAllWindows()
print("Attendance monitoring system stopped.")