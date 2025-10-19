from typing import List

def split_into_chunks(text: str, chunk_size: int = 1400, overlap: int = 150) -> List[str]:
    if not text:
        return []
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= chunk_size:
            cur = (cur + "\n" + p).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)

    if overlap > 0 and len(chunks) > 1:
        stitched = []
        for i, ch in enumerate(chunks):
            if i == 0:
                stitched.append(ch)
            else:
                prev = stitched[-1]
                tail = prev[-overlap:] if len(prev) > overlap else prev
                stitched.append((tail + "\n" + ch).strip())
        chunks = stitched
    return chunks
