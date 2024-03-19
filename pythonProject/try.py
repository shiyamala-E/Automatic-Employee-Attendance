import traceback
from flask import Flask, render_template, request
import os
import cv2
import numpy as np
import mysql.connector
from datetime import datetime
import face_recognition

app = Flask(__name__)

# Configure MySQL connection
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '$Shiyama11'
app.config['MYSQL_DB'] = 'attendance_management'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
db = mysql.connector.connect(
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB'],
    host=app.config['MYSQL_HOST'],
    port=app.config['MYSQL_PORT']
)
cursor = db.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                mobile VARCHAR(15) NOT NULL,
                email VARCHAR(255) NOT NULL,
                registration_num VARCHAR(15) NOT NULL
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_id INT NOT NULL,
                check_in DATETIME NOT NULL,
                check_out DATETIME
                )''')
db.commit()


def capture_image(employee_id):
    try:
        video_capture = cv2.VideoCapture(0)

        while True:
            # Capture frame-by-frame
            ret, frame = video_capture.read()
            if not ret:
                raise ValueError("Failed to capture image from the camera.")

            # Display the resulting frame
            cv2.imshow('Face Detection', frame)

            # Wait for user to press 'c' key to capture image
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                file_path = f'images/{employee_id}.jpg'
                cv2.imwrite(file_path, frame)
                cv2.destroyAllWindows()
                video_capture.release()
                return file_path

            # Exit the loop if 'q' key is pressed
            if key == ord('q'):
                break

        # Release the video capture object
        video_capture.release()
        cv2.destroyAllWindows()
    except Exception as e:
        traceback.print_exc()
        print("Error:", e)
        return None


def insert_employee(name, mobile, email, registration_num):
    sql = "INSERT INTO employees (name, mobile, email, registration_num) VALUES (%s, %s, %s, %s)"
    values = (name, mobile, email, registration_num)
    cursor.execute(sql, values)
    db.commit()
    return cursor.lastrowid


def check_in_out(employee_id):
    try:
        now = datetime.now()
        check_time = now.strftime("%Y-%m-%d %H:%M:%S")
        sql = "SELECT * FROM attendance WHERE employee_id = %s AND check_out IS NULL"
        values = (employee_id,)
        cursor.execute(sql, values)
        existing_record = cursor.fetchone()
        if existing_record:
            sql = "UPDATE attendance SET check_out = %s WHERE id = %s"
            values = (check_time, existing_record[0])
        else:
            sql = "INSERT INTO attendance (employee_id, check_in) VALUES (%s, %s)"
            values = (employee_id, check_time)
        cursor.execute(sql, values)
        db.commit()
    except Exception as e:
        traceback.print_exc()
        print(e)


@app.route('/', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        registration_num = request.form['registration_num']

        # Insert employee data into the database
        employee_id = insert_employee(name, mobile, email, registration_num)

        # Capture employee image
        image_path = capture_image(employee_id)

        return f"Registration successful for {name}! Employee ID: {employee_id}"

    return render_template('registration.html')


@app.route('/check_in_out', methods=['GET', 'POST'])
def check_in_out_page():
    if request.method == 'GET':
        return render_template('check_in_out.html')
    elif request.method == 'POST':
        # Capture employee image
        employee_id = recognize_face()
        if employee_id:
            check_in_out(employee_id)
            return f"Attendance recorded for Employee ID: {employee_id}"
        else:
            return "Not Registered"


def recognize_face():
    try:
        video_capture = cv2.VideoCapture(0)

        # Load registered face encodings
        registered_encodings = []
        registered_ids = []
        for filename in os.listdir('images'):
            if filename.endswith('.jpg'):
                image_path = os.path.join('images', filename)
                image = face_recognition.load_image_file(image_path)
                encoding = face_recognition.face_encodings(image)[0]
                employee_id = os.path.splitext(filename)[0]
                registered_encodings.append(encoding)
                registered_ids.append(employee_id)

        while True:
            # Capture frame-by-frame
            ret, frame = video_capture.read()
            if not ret:
                raise ValueError("Failed to capture image from the camera.")

            # Find faces in the frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            # Check if any face matches registered images
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(registered_encodings, face_encoding)
                if True in matches:
                    matched_id = registered_ids[matches.index(True)]
                    return matched_id

                # Draw rectangle around the detected face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Display the resulting frame
            cv2.imshow('Face Detection', frame)

            # Wait for user to press 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release the video capture object
        video_capture.release()
        cv2.destroyAllWindows()
    except Exception as e:
        traceback.print_exc()
        print("Error:", e)
        return None


if __name__ == '__main__':
    app.run(debug=True)
