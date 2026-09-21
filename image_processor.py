import os
import hashlib
from PIL import Image, ImageEnhance, ExifTags

class ImageProcessor:
    @staticmethod
    def get_image_hash(filepath):
        """Generate SHA256 hash of the image file to detect duplicates."""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as afile:
            buf = afile.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(65536)
        return hasher.hexdigest()

    @staticmethod
    def preprocess_image(filepath, output_filepath):
        """
        Auto-rotate based on EXIF, enhance contrast, and save as JPEG.
        Does NOT alter handwriting or hallucinate data.
        """
        try:
            image = Image.open(filepath)
            
            # 1. Auto-rotate based on EXIF orientation
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                
                exif = image._getexif()
                if exif is not None and orientation in exif:
                    if exif[orientation] == 3:
                        image = image.rotate(180, expand=True)
                    elif exif[orientation] == 6:
                        image = image.rotate(270, expand=True)
                    elif exif[orientation] == 8:
                        image = image.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                # Image doesn't have EXIF data, proceed without rotation
                pass

            # 2. Convert to RGB (in case of RGBA/PNG)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # 3. Enhance Contrast slightly for better OCR
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2) # 20% contrast boost

            # 4. Resize if too large (Gemini has limits, ~3072 is a safe upper bound)
            max_size = 3072
            if max(image.size) > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Save as JPEG
            image.save(output_filepath, 'JPEG', quality=85)
            return output_filepath
            
        except Exception as e:
            print(f"Error preprocessing image {filepath}: {str(e)}")
            return filepath # Return original if preprocessing fails
