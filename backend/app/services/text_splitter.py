import re
from typing import List


def split_text_into_chunks(text: str, max_chunk_size: int = 2500) -> List[str]:
    """
    Chia nhỏ văn bản dài thành các đoạn nhỏ hơn hoặc bằng max_chunk_size ký tự.
    Ưu tiên ngắt tại dấu kết thúc câu (. ? ! …) hoặc dấu xuống dòng,
    đảm bảo không làm đứt gãy từ ngữ hay câu văn.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= max_chunk_size:
        return [clean_text]

    # Phân tách văn bản thành các đơn vị câu / dòng
    sentence_pattern = re.compile(r'([^.?!…\n\r]+[.?!…]+[\s\r\n]*|[^.?!…\n\r]+[\n\r]+|[^\n\r]+$)')
    raw_sentences = sentence_pattern.findall(clean_text)

    if not raw_sentences:
        raw_sentences = clean_text.splitlines(keepends=True)

    chunks: List[str] = []
    current_chunk = ""

    for s in raw_sentences:
        if not s:
            continue

        if len(s) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            sub_chunks = _split_long_sentence(s, max_chunk_size)
            for sub in sub_chunks:
                if len(current_chunk) + len(sub) <= max_chunk_size:
                    current_chunk += (" " if current_chunk and not current_chunk.endswith("\n") else "") + sub
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sub
            continue

        if len(current_chunk) + len(s) <= max_chunk_size:
            current_chunk += s
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = s

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c]


def _split_long_sentence(sentence: str, max_chunk_size: int) -> List[str]:
    """Chia nhỏ một câu siêu dài bằng cách bẻ tại dấu phẩy, chấm phẩy hoặc khoảng trắng."""
    words = sentence.split(" ")
    sub_chunks: List[str] = []
    buf = ""

    for w in words:
        if not w:
            continue
        if len(w) > max_chunk_size:
            if buf:
                sub_chunks.append(buf.strip())
                buf = ""
            for i in range(0, len(w), max_chunk_size):
                sub_chunks.append(w[i : i + max_chunk_size])
            continue

        if len(buf) + len(w) + 1 <= max_chunk_size:
            buf = f"{buf} {w}" if buf else w
        else:
            if buf:
                sub_chunks.append(buf.strip())
            buf = w

    if buf.strip():
        sub_chunks.append(buf.strip())

    return sub_chunks
