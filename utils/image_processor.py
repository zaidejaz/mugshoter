import cv2
import numpy as np
import io

class ImageProcessor:
    @staticmethod
    def crop_image(image_data: io.BytesIO, crop_height: int = 50) -> io.BytesIO:
        # Convert image data to numpy array
        nparr = np.frombuffer(image_data.getvalue(), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Get image dimensions
        height, width, _ = image.shape

        # Crop the image
        cropped_image = image[:height-crop_height, :]

        # Convert back to bytes
        is_success, buffer = cv2.imencode(".jpg", cropped_image)
        if is_success:
            return io.BytesIO(buffer)
        else:
            raise Exception("Failed to encode cropped image")