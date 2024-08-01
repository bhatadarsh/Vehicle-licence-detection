import cv2
import numpy as np
import pytesseract
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime
import openpyxl

TESSERACT_CMD = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
CASCADE_FILE = './indian_license_plate.xml'
DEFAULT_VIDEO = './video1.mp4'
EXCEL_FILE = 'LicensePlates.xlsx'

class LicensePlateRecognizer:
    def __init__(self, master):
        self.master = master
        master.title("License Plate Recognizer")
        self.master.configure(background='#2e3440')
        self.video_source = DEFAULT_VIDEO
        self.paused = False
        self.stop_event = threading.Event()
        self.plate_history = []
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        self.create_widgets()
        self.setup_excel()
        self.start_video()

    def create_widgets(self):
        self.control_frame = ttk.Frame(self.master, style="TFrame")
        self.control_frame.pack(pady=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", background='#4c566a', foreground='white', font=('Helvetica', 10, 'bold'))
        style.configure("TFrame", background='#2e3440')
        style.configure("TLabel", background='#2e3440', foreground='white', font=('Helvetica', 10, 'bold'))
        ttk.Button(self.control_frame, text="Select Video", command=self.select_video, style="TButton").grid(row=0, column=0, padx=5)
        ttk.Button(self.control_frame, text="Pause/Resume", command=self.toggle_pause, style="TButton").grid(row=0, column=1, padx=5)
        ttk.Button(self.control_frame, text="Snapshot", command=self.take_snapshot, style="TButton").grid(row=0, column=2, padx=5)
        ttk.Button(self.control_frame, text="Exit", command=self.master.quit, style="TButton").grid(row=0, column=3, padx=5)
        self.canvas = tk.Canvas(self.master, width=640, height=480, bg='#3b4252', highlightthickness=0)
        self.canvas.pack()
        self.output_frame = ttk.Frame(self.master, style="TFrame")
        self.output_frame.pack(pady=10)
        ttk.Label(self.output_frame, text="Detected Plate:", width=15, style="TLabel").pack(side=tk.LEFT)
        self.output_label = ttk.Label(self.output_frame, text="", width=20, style="TLabel")
        self.output_label.pack(side=tk.LEFT)
        self.history_frame = ttk.Frame(self.master, style="TFrame")
        self.history_frame.pack(pady=10)
        ttk.Label(self.history_frame, text="Plate History:", width=15, style="TLabel").pack(side=tk.LEFT)
        self.history_listbox = tk.Listbox(self.history_frame, width=30, height=5)
        self.history_listbox.pack(side=tk.LEFT)

    def setup_excel(self):
        try:
            self.workbook = openpyxl.load_workbook(EXCEL_FILE)
        except FileNotFoundError:
            self.workbook = openpyxl.Workbook()
            sheet = self.workbook.active
            sheet.title = 'License Plates'
            sheet.append(['Date', 'License Plate'])
            self.workbook.save(EXCEL_FILE)

    def save_to_excel(self, plate_number):
        sheet = self.workbook.active
        sheet.append([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plate_number])
        self.workbook.save(EXCEL_FILE)

    def select_video(self):
        video_file = filedialog.askopenfilename(
            initialdir="./", title="Select Video", filetypes=[("Video files", "*.mp4 *.avi")]
        )
        if video_file:
            self.video_source = video_file
            self.stop_video()
            self.start_video()

    def start_video(self):
        self.stop_video()
        self.cam = cv2.VideoCapture(self.video_source)
        self.cascade = cv2.CascadeClassifier(CASCADE_FILE)
        self.paused = False
        self.stop_event.clear()
        self.video_thread = threading.Thread(target=self.update_frame)
        self.video_thread.start()
    def stop_video(self):
        self.paused = True
        self.stop_event.set()
        if hasattr(self, 'video_thread') and self.video_thread.is_alive():
            self.video_thread.join()
        if hasattr(self, 'cam') and self.cam.isOpened():
            self.cam.release()
        self.canvas.delete("all")

    def toggle_pause(self):
        self.paused = not self.paused

    def take_snapshot(self):
        if self.cam and self.cam.isOpened():
            ret, frame = self.cam.read()
            if ret:
                file_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG files", "*.jpg"), ("All files", "*.*")])
                if file_path:
                    cv2.imwrite(file_path, frame)
                    messagebox.showinfo("Snapshot", "Snapshot saved successfully!")

    def recognize_plate(self, frame):
        plates = self.cascade.detectMultiScale(frame, scaleFactor=1.3, minNeighbors=7)
        plate_number = None
        for (x, y, w, h) in plates:
            plate_img = Image.fromarray(frame[y:y+h, x:x+w])
            plate_number = pytesseract.image_to_string(plate_img, lang='eng').strip()
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if plate_number:
                self.plate_history.append(plate_number)
                self.master.after(0, self.history_listbox.insert, tk.END, plate_number)
                self.master.after(0, self.save_to_excel, plate_number)
        return plate_number
    
    def update_frame(self):
        while not self.stop_event.is_set():
            if not self.paused:
                ret, frame = self.cam.read()
                if not ret:
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                plate_number = self.recognize_plate(frame)
                if plate_number:
                    self.master.after(0, self.update_output_label, plate_number)
                img = Image.fromarray(frame)
                self.master.after(0, self.update_canvas, img)
            self.stop_event.wait(0.03)

    def update_output_label(self, plate_number):
        self.output_label.config(text=f"{plate_number}")

    def update_canvas(self, img):
        tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        self.canvas.image = tk_img

    def __del__(self):
        self.stop_video()

if __name__ == "__main__":
    root = tk.Tk()
    app = LicensePlateRecognizer(root)
    root.mainloop()