"""Fotoğrafları uygulamanın özel klasörüne normalleştirerek kopyalar."""
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageOps


def remove_unused_photo(path, folder, used_paths):
    """Only delete an unreferenced copy directly inside the app's photo folder."""
    if not path: return
    candidate = Path(path).resolve()
    root = Path(folder).resolve()
    if candidate.parent != root: return
    if any(Path(p).resolve()==candidate for p in used_paths if p): return
    candidate.unlink(missing_ok=True)

def import_photo(source, folder):
    source = Path(source)
    if not source.is_file() or source.stat().st_size > 30*1024*1024:
        raise ValueError('Fotoğraf okunamadı veya 30 MB sınırını aşıyor.')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder/(uuid4().hex+'.jpg')
    try:
        with Image.open(source) as opened:
            if opened.width*opened.height > 40_000_000:
                raise ValueError('Fotoğraf çok büyük. Daha düşük çözünürlük seçin.')
            image = ImageOps.exif_transpose(opened).convert('RGB')
            image.thumbnail((1600,1600))
            image.save(destination, 'JPEG', quality=88)
    except Exception as exc:
        if destination.exists(): destination.unlink()
        raise ValueError('Fotoğraf açılamadı. JPG veya PNG deneyin.') from exc
    return str(destination)
