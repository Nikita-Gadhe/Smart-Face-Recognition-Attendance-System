# import cv2
import face_recognition
import numpy  as np
import pickle
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import threading
import csv
import time
import pyttsx3
# from openpyxl import Workbook, load_workbook
# from openpyxl.worksheet.table import Table, TableStyleInfo




class FaceAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2c3e50')
        # Role system (Student / Employee)
        self.current_role = "Student"  # Default
        self.student_data_file = "student_faces.pkl"
        self.employee_data_file = "employee_faces.pkl"
        self.student_attendance = "student_attendance.csv"
        self.employee_attendance = "employee_attendance.csv"
        # Admin authentication
        self.admin_password = "#ITM123"
        # Secret backup code (for emergency access) 
        self.secret_code = "ITM@999"
        # Admin face authentication
        self.admin_face_file = "admin_face.pkl"
        self.admin_encoding = None
        self.load_admin_face()

        # Data storage
        self.data_file = "face_data.pkl"
        self.attendance_file = "attendance.csv"
        self.known_faces = {}  # {name: [encodings_list]}
        self.load_data()
        
        # Camera
        self.cap = None
        self.is_running = False
        
        # Liveness detection parameters
        self.blink_counter = 0
        self.blink_detected = False
        self.ear_threshold = 0.25
        self.motion_detected = False
        self.prev_face_location = None
        # College start time (24-hour format)
        self.college_start_time = "09:15"
        self.half_day_time = "12:00"
        self.college_end_time = "17:00" 

        # Voice engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.setup_gui()

    def load_admin_face(self):
        if os.path.exists(self.admin_face_file):
            with open(self.admin_face_file, "rb") as f:
                self.admin_encoding = pickle.load(f)
    
    def register_admin_face(self):
        messagebox.showinfo(
            "Admin Setup",
            "Look at camera and press SPACE to register admin face"
        )

        cap = cv2.VideoCapture(0)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            cv2.imshow("Register Admin", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):
                faces = face_recognition.face_locations(rgb)

                if len(faces) == 1:
                    enc = face_recognition.face_encodings(rgb, faces)[0]

                    with open(self.admin_face_file, "wb") as f:
                        pickle.dump(enc, f)

                    self.admin_encoding = enc

                    messagebox.showinfo("Success", "Admin face registered!")
                    break
                else:
                    messagebox.showwarning("Warning", "Show exactly one face!")

            elif key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

    def authenticate_admin_face(self):

        if self.admin_encoding is None:
            messagebox.showerror(
                "Error",
                "No admin face registered!\nRun register_admin_face() first."
            )
            return False

        messagebox.showinfo(
            "Admin Login",
            "Look at camera for admin verification"
        )

        cap = cv2.VideoCapture(0)

        success = False
        start_time = time.time()

        while time.time() - start_time < 5:  # 5 seconds scan
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            faces = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, faces)

            for enc in encodings:
                match = face_recognition.compare_faces(
                    [self.admin_encoding],
                    enc,
                    tolerance=0.5
                )

                if match[0]:
                    success = True
                    break

            cv2.imshow("Admin Verification", frame)

            if success:
                break

            if cv2.waitKey(1) == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

        if success:
            messagebox.showinfo("Access Granted", "Admin verified!")
            return True
        else:
            messagebox.showerror("Access Denied", "Admin verification failed!")
            return False
        
    def setup_gui(self):
        # Title
        title_frame = tk.Frame(self.root, bg='#34495e', height=80)
        title_frame.pack(fill='x')
        
        title_label = tk.Label(
            title_frame, 
            text="🎓 Smart Attendance System", 
            font=('Arial', 24, 'bold'),
            bg='#34495e',
            fg='white'
        )
        title_label.pack(pady=20)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Left panel - Camera
        left_panel = tk.Frame(main_frame, bg='#34495e', relief='ridge', bd=3)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        cam_label = tk.Label(left_panel, text="📹 Live Camera", font=('Arial', 14, 'bold'), 
                            bg='#34495e', fg='white')
        cam_label.pack(pady=10)
        self.video_label = tk.Label(left_panel, bg='black')
        self.video_label.pack(padx=10, pady=10, fill='both', expand=True)
        self.status_label = tk.Label(left_panel, text="Status: Camera Off", 
                                     font=('Arial', 12), bg='#34495e', fg='#ecf0f1')
        self.status_label.pack(pady=5)
        
        # Right panel - Controls
        right_panel = tk.Frame(main_frame, bg='#34495e', relief='ridge', bd=3, width=300)
        right_panel.pack(side='right', fill='both', padx=(10, 0))
        # right_panel.pack_propagate(False)
        
        control_label = tk.Label(right_panel, text="⚙️ Controls", font=('Arial', 14, 'bold'),
                                bg='#34495e', fg='white')
        control_label.pack(pady=15)
        self.role_btn = tk.Button(
        right_panel,
        text="🔄 Switch to Employee",
        bg='#8e44ad',
        fg='white',
        command=self.switch_role,
        font=('Arial', 12, 'bold')
        )
        self.role_btn.pack(pady=10)

        # Buttons
        btn_style = {
            'font': ('Arial', 12, 'bold'),
            'width': 20,
            'height': 2,
            'bd': 0,
            'cursor': 'hand2'
        }   
        self.register_btn = tk.Button(
            right_panel,
            text="👤 Register New Student",
            bg='#27ae60',
            fg='white',
            command=self.register_face,
            **btn_style
        )
        self.register_btn.pack(pady=10, padx=20)
        self.start_btn = tk.Button(
            right_panel,
            text="▶️ Start Attendance",
            bg='#3498db',
            fg='white',
            command=self.start_camera,
            **btn_style
        )
        self.start_btn.pack(pady=10, padx=20)
        self.stop_btn = tk.Button(
            right_panel,
            text="⏹️ Stop Camera",
            bg='#e74c3c',
            fg='white',
            command=self.stop_camera,
            state='disabled',
            **btn_style
        )
        self.stop_btn.pack(pady=10, padx=20)
        self.view_btn = tk.Button(
            right_panel,
            text="📋 View Attendance",
            bg='#f39c12',
            fg='white',
            command=self.view_attendance,
            **btn_style
        )
        self.view_btn.pack(pady=10, padx=20)
        
        # Info panel
        info_frame = tk.Frame(right_panel, bg='#2c3e50', relief='sunken', bd=2)
        info_frame.pack(fill='x', pady=10, padx=20)
        info_title = tk.Label(info_frame, text="ℹ️ Information", font=('Arial', 11, 'bold'),
                             bg='#2c3e50', fg='#ecf0f1')
        info_title.pack(pady=10)
        
        total_students = len(self.known_faces)
        info_text = f"Registered Students: {total_students}\n\n"
        info_text += "Features:\n"
        info_text += "• Liveness Detection\n"
        info_text += "• Multi-photo Storage\n"
        info_text += "• Color Recognition\n"
        info_text += "• Real-time Processing" 
        # Table (Treeview)
        columns = ("Item", "Details")
        self.info_table = ttk.Treeview(info_frame, columns=columns, show="headings", height=6)

        self.info_table.heading("Item", text="Item")
        self.info_table.heading("Details", text="Details")

        self.info_table.column("Item", width=150)
        self.info_table.column("Details", width=200)

        self.info_table.pack(pady=5, padx=10, fill="x")

        self.update_info_table()

       
        # Scrollable photo panel
        photo_container = tk.Frame(right_panel, bg='#2c3e50', relief='sunken', bd=2)
        photo_container.pack(fill='both', expand=True, pady=10, padx=20)

        # Canvas + Scrollbar
        canvas = tk.Canvas(photo_container, bg='#2c3e50', highlightthickness=0)
        scrollbar = ttk.Scrollbar(photo_container, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.photo_title = tk.Label(
            scrollable_frame,
            text=f"📸 {self.current_role} Photos",
            font=('Arial', 11, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        self.photo_title.pack(pady=5)

        # Listbox
        self.photo_listbox = tk.Listbox(scrollable_frame, height=8)
        self.photo_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        self.remove_btn = tk.Button(
            scrollable_frame,
            text="🗑 Remove Selected Student",
            bg='#c0392b',
            fg='white',
            command=self.remove_selected_student
        )
        self.remove_btn.pack(pady=5, fill='x')
        self.update_photo_list()
        self.status_label.config(
            text=f"Attendance Time: {self.college_start_time} - {self.college_end_time}"
)

    def load_data(self):
        file = self.student_data_file if self.current_role == "Student" else self.employee_data_file
        if os.path.exists(file):
            with open(file, 'rb') as f:
                self.known_faces = pickle.load(f)
        else:
            self.known_faces = {}

    def switch_role(self):
        if self.current_role == "Student":
            self.current_role = "Employee"
            self.role_btn.config(text="🔄 Switch to Student")
            self.register_btn.config(text="👤 Register New Employee")
        else:
            self.current_role = "Student"
            self.role_btn.config(text="🔄 Switch to Employee")
            self.register_btn.config(text="👤 Register New Student")
        self.photo_title.config(text=f"📸 {self.current_role} Photos")    

        self.load_data()
        self.update_photo_list()
        self.update_info()
        messagebox.showinfo("Role Changed", f"Current mode: {self.current_role}")
    
    def authenticate_admin(self):
        password = simpledialog.askstring(
            "Admin Authentication",
            "Enter Admin Password:",
            show="*"
        )

        if password == self.admin_password:
            return True
        else:
            messagebox.showerror(
                "Access Denied",
                "Incorrect password!"
            )
            return False
        
    def authenticate_admin_backup(self):

        code = simpledialog.askstring(
            "Backup Authentication",
            "Enter Admin Password OR Secret Code:",
            show="*"
        )

        if code == self.admin_password or code == self.secret_code:
            messagebox.showinfo("Access Granted", "Backup authentication successful!")
            return True
        else:
            messagebox.showerror("Access Denied", "Wrong password or secret code!")
            return False    

    def save_data(self):
        file = self.student_data_file if self.current_role == "Student" else self.employee_data_file
        with open(file, 'wb') as f:
            pickle.dump(self.known_faces, f)
             
    def calculate_ear(self, eye_points):
        """Calculate Eye Aspect Ratio for blink detection"""
        if len(eye_points) < 6:
            return 0.3
        
        # Vertical distances
        A = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
        B = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
        
        # Horizontal distance
        C = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def detect_liveness(self, frame, face_location):
        """Advanced liveness detection"""

        # 🔥 Anti-phone screen detection (ADD THIS PART)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

        if np.var(laplacian) < 50:
            return False  # Likely phone screen

        # ---------------------------
        # Existing motion detection
        if self.prev_face_location is not None:
            movement = np.linalg.norm(
                np.array(face_location) - np.array(self.prev_face_location)
            )
            if movement > 5:
                self.motion_detected = True

        self.prev_face_location = face_location

        # Blink detection
        try:
            face_landmarks = face_recognition.face_landmarks(frame)
            if face_landmarks:
                left_eye = face_landmarks[0].get('left_eye', [])
                right_eye = face_landmarks[0].get('right_eye', [])

                if left_eye and right_eye:
                    left_ear = self.calculate_ear(left_eye)
                    right_ear = self.calculate_ear(right_eye)
                    ear = (left_ear + right_ear) / 2.0

                    if ear < self.ear_threshold:
                        self.blink_detected = True
        except:
            pass

        # 🔥 Stronger liveness rule
        is_live = self.motion_detected and self.blink_detected

        return is_live

    
    def register_face(self):
        """Register new student with multiple photos"""
        # 🔐 Admin authentication
        if not self.authenticate_admin_face():
            if not self.authenticate_admin_backup():
                return

        name = simpledialog.askstring(
            "Register",
            f"Enter {self.current_role} Name:"
        )

        if not name:
            return
        
        if name in self.known_faces:
            messagebox.showerror("Error", "Student already registered!")
            return
        
        # Capture multiple photos
        messagebox.showinfo("Instructions", 
                          f"We will capture 1 photos of {name}.\n\n"
                          "Please:\n"
                          "1. Look straight at camera\n"
                          "2. Ensure good lighting\n\n"
                          "Click OK to start")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        messagebox.showinfo("Instructions",
                            f"Look at camera and press SPACE to capture photo")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera frame failed (register)")
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cv2.putText(frame, "Press SPACE to capture",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2)
            cv2.imshow("Register Face", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                face_locations = face_recognition.face_locations(rgb_frame)
                if len(face_locations) == 1:
                    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    if not encodings:
                        messagebox.showerror("Error", "No face encoding found!")
                        continue

                    face_encoding = encodings[0]

                    # 🔥 PHOTO SAVE CODE YAHAN LAGEGA
                    if self.current_role == "Student":
                        folder = "students"
                    else:
                        folder = "employees"

                    os.makedirs(folder, exist_ok=True)

                    filepath = os.path.join(folder, f"{name}.jpg")
                    cv2.imwrite(filepath, frame)

                    # Face encoding save
                    self.known_faces[name] = [face_encoding]
                    self.save_data()

                    messagebox.showinfo(
                        "Success",
                        f"{name} registered successfully!"
                    )
                    break

                else:
                    messagebox.showwarning(
                        "Warning",
                        "Ensure exactly one face is visible!"
                    )
            elif key == 27:
                break
        cap.release()
        cv2.destroyAllWindows()
        self.update_info()
        self.update_photo_list()
    
    def start_camera(self):
        """Start attendance camera"""
        if self.is_running:
            return
            
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.is_running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.register_btn.config(state='disabled')
        self.status_label.config(text="Status: Camera Active - Scanning...", fg='#2ecc71')
        # Start video thread
        self.video_thread = threading.Thread(target=self.process_video, daemon=True)
        self.video_thread.start()
    
    def process_video(self):
        """Process video for face recognition"""
        consecutive_frames = 0
        last_name = None
        attendance_marked = set()
        while self.is_running:
            # print("Camera opened:", self.cap.isOpened())
            ret, frame = self.cap.read()
            # print("Frame status:", ret)
            
            if not ret:
                print("Camera frame failed (attendance)")
                self.root.after(0, self.stop_camera)
                break

            # Mirror frame
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                is_live = self.detect_liveness(rgb_frame, face_location)
                name = "Unknown"
                confidence = 0
                
                for known_name, known_encodings in self.known_faces.items():
                    # FIX: ensure encodings are always a list
                    if not isinstance(known_encodings, list):
                        known_encodings = [known_encodings]
                    matches = face_recognition.compare_faces(
                        known_encodings,
                        face_encoding,
                       tolerance=0.5
                    )
                    face_distances = face_recognition.face_distance(
                        known_encodings,
                        face_encoding
                    )

                    if True in matches:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_name
                            confidence = (1 - face_distances[best_match_index]) * 100
                            break
                
                # Draw box
                top, right, bottom, left = face_location
                
                if name != "Unknown" and is_live:
                    color = (0, 255, 0)  # Green
                    label = f"{name} ({confidence:.1f}%)"
                    
                    # Count consecutive detections
                    if name == last_name:
                        consecutive_frames += 1
                    else:
                        consecutive_frames = 1
                        last_name = name
                    
                    # Mark attendance after 10 consecutive frames
                    if consecutive_frames >= 3 and name not in attendance_marked:
                        self.mark_attendance(name)
                        attendance_marked.add(name)
                        consecutive_frames = 0
                        
                elif name != "Unknown" and not is_live:
                    color = (0, 165, 255)  # Orange
                    label = "Fake Detection!"
                else:
                    color = (0, 0, 255)  # Red
                    label = "Unknown"
                    consecutive_frames = 0
                    last_name = None
                
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 6, bottom - 6),
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            # Display instructions
            cv2.putText(frame, "Look at camera for attendance", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Convert for tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((640, 480))
            imgtk = ImageTk.PhotoImage(image=img)
            self.root.after(0, self.update_video_label, imgtk)
            time.sleep(0.01)

    def update_video_label(self, imgtk):
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()
    
    def mark_attendance(self, name):

        attendance_file = self.student_attendance if self.current_role == "Student" else self.employee_attendance

        now = datetime.now()
        date_string = now.strftime("%Y-%m-%d")
        time_string = now.strftime("%H:%M:%S")

        start_time = datetime.strptime(self.college_start_time, "%H:%M").time()
        end_time = datetime.strptime(self.college_end_time, "%H:%M").time()
        current_time = now.time()

        half_day_time = datetime.strptime(self.half_day_time, "%H:%M").time()

        if current_time <= start_time:
            status = "On Time"
        elif current_time <= half_day_time:
            status = "Late"
        else:
            status = "Half Day"
        # 🔊 Late announcement
        if status == "Late":
            self.speak(f"{name}, you are late today")
        elif status == "Half Day":
            self.speak(f"{name}, you are marked half day")
    


        records = []
        file_exists = os.path.exists(attendance_file)

        # Read existing file
        if file_exists:
            with open(attendance_file, "r") as f:
                records = list(csv.reader(f))

        # Add header if empty
        if not records:
            records.append(["Name", "Date", "In Time", "Out Time", "Status"])

        found = False

        # Check if already exists today
        for i in range(1, len(records)):
            row = records[i]

            if row[0] == name and row[1] == date_string:

                # If OUT time empty → fill it
                if row[3] == "":
                    records[i][3] = time_string
                    self.speak(f"Goodbye {name}")

                found = True
                break

        if not found:
            records.append([name, date_string, time_string, "", status])

            if status == "On Time":
                self.speak(f"Welcome {name}, you are on time")

            elif status == "Late":
                self.speak(f"Warning {name}, you are late today")

            elif status == "Half Day":
                self.speak(f"{name}, you are marked half day")

      
        # Save back to file
        with open(attendance_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(records)

        self.status_label.config(
            text=f"{name} attendance updated!",
            fg='#2ecc71'
        )

    def check_absent_students(self):

        attendance_file = self.student_attendance if self.current_role == "Student" else self.employee_attendance

        if not os.path.exists(attendance_file):
            return

        now = datetime.now()
        end_time = datetime.strptime(self.college_end_time, "%H:%M").time()

        # Only run after college end time
        if now.time() < end_time:
            return

        records = []

        with open(attendance_file, "r") as f:
            reader = csv.reader(f)

            for row in reader:
                # Skip empty or broken rows
                while len(row) < 5:
                   row.append("")

                records.append(row)

        if len(records) <= 1:
            return

        today = now.strftime("%Y-%m-%d")

        for i in range(1, len(records)):
            row = records[i]

            # Safe unpack
            name, date, in_time, out_time, status = row

            if date == today and out_time == "":
                records[i][4] = "Absent"

        # Save back
        with open(attendance_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(records)
 


    def stop_camera(self):
        """Stop camera"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.video_label.config(image='')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.register_btn.config(state='normal')
        self.status_label.config(text="Status: Camera Off", fg='#ecf0f1')
        
        # Reset liveness parameters
        self.blink_detected = False
        self.motion_detected = False
        self.prev_face_location = None
        self.check_absent_students()


    def view_attendance(self):

        attendance_file = self.student_attendance if self.current_role == "Student" else self.employee_attendance

        if not os.path.exists(attendance_file):
            messagebox.showinfo("Attendance", "No attendance records found!")
            return

        view_window = tk.Toplevel(self.root)
        view_window.title("Attendance Records")
        view_window.geometry("750x400")
        view_window.configure(bg='#2c3e50')

        title = tk.Label(view_window,
                            text="📋 Attendance Records",
                            font=('Arial', 16, 'bold'),
                            bg='#2c3e50',
                            fg='white')
        title.pack(pady=10)

        frame = tk.Frame(view_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Table columns
        columns = ("Name", "Date", "In Time", "Out Time", "Status")

        tree = ttk.Treeview(frame, columns=columns, show="headings")

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=140)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        # Load CSV data
        with open(attendance_file, "r") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header

            for row in reader:
                # ensure row has 5 columns
                while len(row) < 5:
                    row.append("")
                tree.insert("", "end", values=row)

    def update_info_table(self):
        # Clear old data
        for row in self.info_table.get_children():
            self.info_table.delete(row)

        # Insert table data
        self.info_table.insert("", "end", values=("Registered Students", len(self.known_faces)))
        self.info_table.insert("", "end",
            values=("Attendance Time",
            f"{self.college_start_time} - {self.college_end_time}"))

        self.info_table.insert("", "end", values=("Feature", "Liveness Detection"))
        self.info_table.insert("", "end", values=("Feature", "Multi-photo Storage"))
        self.info_table.insert("", "end", values=("Feature", "Color Recognition"))
        self.info_table.insert("", "end", values=("Feature", "Real-time Processing"))
    
    def update_info(self):
        self.update_info_table()

    def update_photo_list(self):
        self.photo_listbox.delete(0, tk.END)
    
        if not self.known_faces:
            self.photo_listbox.insert(tk.END, "No registered data")
            return

        for name in self.known_faces.keys():
            self.photo_listbox.insert(tk.END, name)

    def remove_selected_student(self):
        selection = self.photo_listbox.curselection()

        if not selection:
            messagebox.showerror(
                "Error",
                f"{self.current_role} already registered!"
            )
            return

        name = self.photo_listbox.get(selection[0])
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to remove {name}?"
        )

        if confirm:
            del self.known_faces[name]
            self.save_data()
            self.update_photo_list()
            self.update_info()
            messagebox.showinfo(
                "Removed",
                f"{name} removed successfully!"
            )

    def on_closing(self):
        """Clean up on exit"""
        self.stop_camera()
        self.check_absent_students()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FaceAttendanceSystem(root)
    # Run once to register admin face
    # app.register_admin_face()
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()