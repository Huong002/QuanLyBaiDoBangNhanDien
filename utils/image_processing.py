import cv2
# utils/image_processing.py
import re
from ultralytics import YOLO
from PIL import Image
import pytesseract
import numpy as np

yolo_model = YOLO('runs/train3/weights/best.pt')

def detect_plate_yolo(image_path):
    results = yolo_model(image_path)
    print("YOLO results:", results)
    boxes = results[0].boxes.xyxy.cpu().numpy() if hasattr(results[0].boxes, 'xyxy') else []
    print("Detected boxes:", boxes)
    if len(boxes) == 0:
        print("Không tìm thấy biển số!")
        return None, None
    x1, y1, x2, y2 = map(int, boxes[0])
    image = Image.open(image_path)
    plate_crop = image.crop((x1, y1, x2, y2))
    plate_crop.save("debug_plate_crop.jpg")
    number_plate = read_number_plate(plate_crop)
    print("Ktet qua ORC: ", number_plate)
    result_output = format_plate(number_plate)
    print("Ket qua sau format:", result_output)
    return result_output, plate_crop

def preprocess_for_ocr(pil_img):
    img = np.array(pil_img)
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)
    

# ham chuan hoa dinh dang dau ra
def format_plate(text):
    text = re.sub(r'[^A-Z0-9\-.]', '', text.upper())
    return text

def read_number_plate(image_or_path):
    path_to_tesseract = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = path_to_tesseract
    if isinstance(image_or_path, str):
        image = Image.open(image_or_path)
    else:
        image = image_or_path
    image = preprocess_for_ocr(image)
    text = pytesseract.image_to_string(image, lang='eng', config='--psm 7')
    if not text.strip():
        text = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
    number_plate = "".join(char for char in str(text) if not char.isspace())
    return number_plate