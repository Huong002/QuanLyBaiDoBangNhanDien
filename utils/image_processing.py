import cv2

# utils/image_processing.py
import re
from ultralytics import YOLO
from PIL import Image
import pytesseract
import numpy as np

try:
    from paddleocr import PaddleOCR

    PADDLE_OCR_AVAILABLE = True
    paddle_ocr = None
except ImportError:
    PADDLE_OCR_AVAILABLE = False
    paddle_ocr = None
    print("PaddleOCR không được cài đặt. Sử dụng Tesseract OCR.")


def get_paddle_ocr():
    """Lazy loading PaddleOCR để tránh lỗi khởi tạo khi import module"""
    global paddle_ocr, PADDLE_OCR_AVAILABLE
    if paddle_ocr is None and PADDLE_OCR_AVAILABLE:
        try:
            paddle_ocr = PaddleOCR(lang="en")
            print("PaddleOCR đã được khởi tạo thành công!")
        except Exception as e:
            print(f"Lỗi khởi tạo PaddleOCR: {e}")
            PADDLE_OCR_AVAILABLE = False
    return paddle_ocr


yolo_model = YOLO("runs/train3/weights/best.pt")


def detect_plate_yolo(image_path, use_paddle_ocr=True):
    results = yolo_model(image_path)
    boxes = (
        results[0].boxes.xyxy.cpu().numpy() if hasattr(results[0].boxes, "xyxy") else []
    )
    print("Detected boxes:", boxes)
    if len(boxes) == 0:
        print("Không tìm thấy biển số!")
        return None, None
    x1, y1, x2, y2 = map(int, boxes[0])
    image = Image.open(image_path)
    plate_crop = image.crop((x1, y1, x2, y2))
    plate_crop.save("debug_plate_crop.jpg")

    number_plate = read_number_plate(plate_crop, use_paddle=use_paddle_ocr)
    print(
        f"Ket qua OCR ({'PaddleOCR' if use_paddle_ocr and PADDLE_OCR_AVAILABLE else 'Tesseract'}): ",
        number_plate,
    )
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
    text = re.sub(r"[^A-Z0-9\-.]", "", text.upper())
    return text


def read_number_plate_paddle_ocr(image_or_path):
    """
    Đọc biển số xe sử dụng PaddleOCR
    """
    if not PADDLE_OCR_AVAILABLE:
        print("PaddleOCR không khả dụng, chuyển sang sử dụng Tesseract")
        return read_number_plate_tesseract(image_or_path)

    ocr_instance = get_paddle_ocr()
    if ocr_instance is None:
        print("Không thể khởi tạo PaddleOCR, chuyển sang sử dụng Tesseract")
        return read_number_plate_tesseract(image_or_path)

    try:
        if isinstance(image_or_path, str):
            image = cv2.imread(image_or_path)
        elif isinstance(image_or_path, Image.Image):
            image = cv2.cvtColor(np.array(image_or_path), cv2.COLOR_RGB2BGR)
        else:
            image = image_or_path

        result = ocr_instance.ocr(image, cls=True)

        # Xử lý kết quả
        if result and result[0]:
            texts = []
            for line in result[0]:
                if line[1][1] > 0.5:  
                    texts.append(line[1][0])

            full_text = "".join(texts)
            number_plate = "".join(char for char in full_text if not char.isspace())
            return number_plate
        else:
            print("PaddleOCR không tìm thấy text, thử với Tesseract")
            return read_number_plate_tesseract(image_or_path)

    except Exception as e:
        print(f"Lỗi khi sử dụng PaddleOCR: {e}")
        return read_number_plate_tesseract(image_or_path)


def read_number_plate_tesseract(image_or_path):
    """
    Đọc biển số xe sử dụng Tesseract OCR (hỗ trợ cả 1 hàng và 2 hàng)
    """
    path_to_tesseract = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = path_to_tesseract
    if isinstance(image_or_path, str):
        image = Image.open(image_or_path)
    else:
        image = image_or_path
    image = preprocess_for_ocr(image)
    text = pytesseract.image_to_string(image, lang="eng", config="--psm 6")
    number_plate = "".join(char for char in text if not char.isspace())
    return number_plate


def read_number_plate(image_or_path, use_paddle=True):
    """
    Hàm chính để đọc biển số xe
    Args:
        image_or_path: Đường dẫn ảnh hoặc đối tượng Image
        use_paddle: True để sử dụng PaddleOCR, False để sử dụng Tesseract
    """
    if use_paddle and PADDLE_OCR_AVAILABLE:
        return read_number_plate_paddle_ocr(image_or_path)
    else:
        return read_number_plate_tesseract(image_or_path)
