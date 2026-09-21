import os
import shutil
import time
from database import create_job, create_docket
from app import process_docket_async
from image_processor import ImageProcessor
from config import Config

def test_pipeline():
    images = [
        "C:/Users/ANKUR THAKUR/.gemini/antigravity/brain/c7c4d8a3-b2a4-4856-970f-8e881893607e/.user_uploaded/media_1789940194603.jpg",
        "C:/Users/ANKUR THAKUR/.gemini/antigravity/brain/c7c4d8a3-b2a4-4856-970f-8e881893607e/.user_uploaded/media_1789940194604.jpg",
        "C:/Users/ANKUR THAKUR/.gemini/antigravity/brain/c7c4d8a3-b2a4-4856-970f-8e881893607e/.user_uploaded/media_1789940194610.jpg",
        "C:/Users/ANKUR THAKUR/.gemini/antigravity/brain/c7c4d8a3-b2a4-4856-970f-8e881893607e/.user_uploaded/media_1789940194614.jpg",
        "C:/Users/ANKUR THAKUR/.gemini/antigravity/brain/c7c4d8a3-b2a4-4856-970f-8e881893607e/.user_uploaded/media_1789940194617.jpg"
    ]
    
    job_id = create_job(len(images))
    print(f"Created Job {job_id} for {len(images)} images.")
    
    for i, img_path in enumerate(images):
        if not os.path.exists(img_path):
            print(f"Error: {img_path} not found.")
            continue
            
        filename = f"test_img_{i}.jpg"
        dest_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        shutil.copy(img_path, dest_path)
        
        image_hash = ImageProcessor.get_image_hash(dest_path)
        docket_id = create_docket(job_id, filename, image_hash, f"Original_{i}.jpg")
        
        print(f"Processing docket {docket_id}...")
        process_docket_async(docket_id, dest_path)
        
    print("Done triggering pipeline. Wait a bit for async tasks to finish...")

if __name__ == "__main__":
    test_pipeline()
