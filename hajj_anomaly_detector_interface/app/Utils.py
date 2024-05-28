import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from keras.utils import load_img, img_to_array
# from keras.preprocessing.image import load_img, img_to_array # new method the other one is deprecated in the new version of keras
from keras.applications.imagenet_utils import preprocess_input
from keras.models import load_model
from ultralytics import YOLO
# from ultralytics.engine.results import Boxes
import numpy as np
import cv2
from PIL import Image

from datetime import datetime
import secrets
import random

from werkzeug.datastructures import FileStorage


class Utils:
    KERAS = 'keras'
    YOLO = 'yolo'

    @staticmethod
    def predict(keras_model, img_path):
        # image preprocessing
        img = load_img(img_path, target_size=(224, 224))
        x = img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        return keras_model.predict(x)[0]

    @staticmethod
    def localize(yolo_model, image_path, output_path, confidence_threshold: float=0.50):
        BOX_COLOR = (0, 231,252)
        TEXT_COLOR = (255, 246, 233)
        TEXT_BORDER_COLOR = (0, 0, 0)

        results = yolo_model(image_path)

        image = cv2.imread(image_path)
        _, image_width = image.shape[:2]


        boxes = results[0].boxes
        for box in boxes:
            confidence = box.conf[0].item()

            if confidence >= confidence_threshold:
                x1, y1, x2, y2 = box.xyxy[0].numpy().astype(int)
                label = Utils.get_labels()[int(box.cls[0].item())]

                cv2.rectangle(image, (x1, y1), (x2, y2), BOX_COLOR, 1)

                text = f'{label}: {confidence:.2f}'
                text_position = Utils.get_text_position(x1, x2, y1, len(label), image_width)
                font_scale = 0.45
                cv2.putText(image, text, text_position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_BORDER_COLOR, 3)
                cv2.putText(image, text, text_position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_COLOR, 2)


        # Save the image with bounding boxes
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        image_name = secrets.token_hex(8) + os.path.splitext(image_path)[1]
        image_path = os.path.join(output_path, image_name)

        cv2.imwrite(image_path, image)
       
        return image_name
    
    @staticmethod
    def get_text_position(x1, x2, y1, label_len, image_width):
        CHAR_WIDTH = 7
        if x2 > image_width - 100:
            text_position = (x1 - (label_len * CHAR_WIDTH), y1 - 10)
        elif x1 < 30:
            text_position = (x1, y1 - 10)
        else:
            text_position = (x1 - 30, y1 - 10)

        return text_position
    @staticmethod
    def load_model(model_path: str, model_type: str = 'keras'):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at path: {model_path}")
        
        if model_type == 'keras':
            return load_model(model_path)
        elif model_type == 'yolo':
            return YOLO(model=model_path)
        else:
            raise ValueError("Unknown model type. Please provide a valid model path.")
            
    @staticmethod
    def get_labels():
        return ['Diff_Direction', 'Non_Pedestrain', 'Opp_Direction', 'Running', 'Sitting', 'Sleeping', 'Standing']
    
    @staticmethod
    def get_env_variable(key: str):
        return os.environ.get(key)
    
    @staticmethod
    def generate_random_number(start: int = 0, end: int = 100):
        return random.randint(start, end)

    @staticmethod
    def save_image(image, path: str, resize: bool = True):
        if not os.path.exists(path):
            os.makedirs(path)

        image_exe = ''
        if isinstance(image, FileStorage):
            image_exe = os.path.splitext(image.filename)[1]
        elif isinstance(image, Image.Image):
            image_exe = '.png' # TODO: i assumed the image is .png => only accept .png images

        image_name = secrets.token_hex(8) + image_exe
        image_path = os.path.join(path, image_name)

        if resize:
            # resize image
            output_size = (125, 125)
            resized_image = Image.open(image)
            resized_image.thumbnail(output_size)
            resized_image.save(image_path)
        else:
            image.save(image_path)

        return image_name

    @staticmethod
    def validate_file(image: FileStorage, allowed_extensions: list):
        return '.' in image.filename and image.filename.rsplit('.', 1)[1].lower() in allowed_extensions    


class Logger:
    __COLORS = {
        'INFO': '\033[94m',      # Blue
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'SUCCESS': '\033[92m',   # Green
        'PLAIN': '\033[0m',      # Plain Text
    }
    __ENDCOLOR = '\033[0m'       # Reset color

    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    SUCCESS = 'SUCCESS'
    PLAIN = 'PLAIN'


    def log(self, message: str = "", severity: str = PLAIN, show_time: bool = True, show_severity: bool = True, new_line: bool = True):
        """Log a message to the console with a specific color based on the severity.
        
        Keyword arguments:
        message -- the message to log
        severity -- the severity of the message (default PLAIN)
        show_time -- whether to show the time in the log (default True)
        show_severity -- whether to show the severity in the log (default True)
        new_line -- whether to add a new line at the end of the log (default True)

        Raises:
        ValueError -- if the severity is not valid


        Example:
        logger = Logger()
        logger.log("This is an info message", Logger.INFO)

        Returns:
        None
        """
        
        if severity not in self.__COLORS:
            raise ValueError(f"Invalid severity: {severity}. Allowed values are {', '.join(self.__COLORS.keys())}.")


        color = self.__COLORS[severity]
        end_color = self.__ENDCOLOR if color != self.__COLORS[self.PLAIN] else ""
        time = datetime.now().strftime("%H:%M:%S") if show_time else ""
        severity = f"[{severity}]" if show_severity else ""
        end = "\n" if new_line else ""

        formatted_message = f"{time} {color}{severity} {message}{end_color}"
        print(formatted_message, end=end)
