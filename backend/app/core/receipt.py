"""Tạo biên lai thanh toán (Receipt/Invoice) định dạng PDF chuẩn."""
from datetime import datetime


def generate_receipt_pdf(
    order_code: str,
    user_email: str,
    plan_name: str,
    original_amount: int,
    discount_amount: int,
    final_amount: int,
    credits: int,
    payment_method: str,
    paid_at: datetime,
) -> bytes:
    """
    Tạo tài liệu PDF 1.4 hợp lệ chứa thông tin hóa đơn thanh toán của Voxify.
    Hoàn toàn bằng Python thuần, không phụ thuộc thư viện bên ngoài.
    """
    paid_date_str = paid_at.strftime("%d/%m/%Y %H:%M:%S UTC")

    # Sanitize chuỗi để chỉ chứa ASCII hoặc text an toàn cho PDF latin-1
    def sanitize(text: str) -> str:
        replacements = {
            "đ": "d", "Đ": "D", "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
            "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
            "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
            "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
            "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
            "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
            "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
            "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
            "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
            "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
            "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
            "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
            "(": "[", ")": "]",
        }
        res = ""
        for ch in text:
            if ch in replacements:
                res += replacements[ch]
            elif ord(ch) < 128:
                res += ch
            else:
                res += "_"
        return res

    clean_order_code = sanitize(order_code)
    clean_user_email = sanitize(user_email)
    clean_plan_name = sanitize(plan_name)
    clean_method = sanitize(payment_method.upper())

    content_lines = [
        "BT",
        "/F2 20 Tf",
        "50 780 Td (VOXIFY AI STUDIO - RECEIPT / HOA DON) Tj",
        "/F1 10 Tf",
        "0 -25 Td (Platform: https://voxify.app | Email support: support@voxify.app) Tj",
        "0 -15 Td (-------------------------------------------------------------------------------------------------) Tj",
        "/F2 12 Tf",
        "0 -25 Td (THONG TIN DON HANG / ORDER DETAILS) Tj",
        "/F1 10 Tf",
        f"0 -20 Td (Ma don hang / Order Code: #{clean_order_code}) Tj",
        f"0 -18 Td (Khach hang / Customer: {clean_user_email}) Tj",
        f"0 -18 Td (Ngay thanh toan / Paid Date: {paid_date_str}) Tj",
        f"0 -18 Td (Phuong thuc / Payment Method: {clean_method}) Tj",
        "0 -18 Td (Trang thai / Status: DA THANH TOAN / SUCCESSFUL) Tj",
        "0 -20 Td (-------------------------------------------------------------------------------------------------) Tj",
        "/F2 12 Tf",
        "0 -25 Td (CHI TIET DICH VU / SERVICE SUMMARY) Tj",
        "/F1 10 Tf",
        f"0 -20 Td (Goi dich vu / Plan Name: {clean_plan_name}) Tj",
        f"0 -18 Td (Gia goc / Original Price: {original_amount:,} VND) Tj",
        f"0 -18 Td (Giam gia / Discount: -{discount_amount:,} VND) Tj",
        f"0 -18 Td (Credit nhan duoc / Credits Added: +{credits:,} credits) Tj",
        "0 -20 Td (-------------------------------------------------------------------------------------------------) Tj",
        "/F2 13 Tf",
        f"0 -25 Td (TONG CONG / TOTAL PAID: {final_amount:,} VND) Tj",
        "0 -20 Td (-------------------------------------------------------------------------------------------------) Tj",
        "/F1 9 Tf",
        "0 -30 Td (Cam on quy khach da tin tuong va dong hanh cung Voxify AI!) Tj",
        "0 -15 Td (Chung tu nay duoc tao tu dong tu he thong Voxify. Khong can chu ky tay.) Tj",
        "ET",
    ]

    stream_data = "\n".join(content_lines).encode("latin-1")
    stream_len = len(stream_data)

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n" + stream_data + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n",
    ]

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = b""
    offsets = [0]
    curr_offset = len(header)
    for obj in objects:
        offsets.append(curr_offset)
        curr_offset += len(obj)
        body += obj

    xref_offset = curr_offset
    xref = b"xref\n0 " + str(len(objects) + 1).encode("ascii") + b"\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        xref += f"{offset:010d} 00000 n \n".encode("ascii")

    trailer = (
        b"trailer\n<< /Size " + str(len(objects) + 1).encode("ascii") +
        b" /Root 1 0 R >>\nstartxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
    )
    return header + body + xref + trailer
