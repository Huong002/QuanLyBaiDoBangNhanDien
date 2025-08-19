# utils/image_processing.py
from pytesseract import pytesseract
from PIL import Image
from app import check_np, check_np_status, insert_np, update_np, get_province

def read_number_plate(image_path):
    path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Đường dẫn đến Tesseract
    pytesseract.tesseract_cmd = path_to_tesseract
    image = Image.open(image_path)

    # Trích xuất văn bản từ ảnh
    text = pytesseract.image_to_string(image, lang='eng')
    number_plate = "".join(char for char in str(text) if not char.isspace())

    print("-----------------------------------")
    print(f"Xe có biển số: {number_plate}")
    if number_plate:
        province = get_province(number_plate)
        print(f"Tỉnh/Thành phố: {province}")
    print("-----------------------------------")

    if number_plate:
        check = check_np(number_plate)
        if check == 0:
            insert_np(number_plate)
        else:
            check2 = check_np_status(number_plate)
            if check2 and check2[2] == 1:  # Trạng thái = 1 (xe trong bãi)
                update_np(check2[0])
            else:
                insert_np(number_plate)
    else:
        print("Không xác định được biển số xe")