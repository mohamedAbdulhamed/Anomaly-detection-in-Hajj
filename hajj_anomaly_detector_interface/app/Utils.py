import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# from tensorflow.keras.utils import load_img, img_to_array
from keras.preprocessing.image import load_img, img_to_array
from keras.applications.imagenet_utils import preprocess_input
from keras.models import load_model
import numpy as np
from PIL import Image

from datetime import datetime
import secrets
import random

from werkzeug.datastructures import FileStorage
# from werkzeug.utils import secure_filename

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class Utils:
    @staticmethod
    def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def load_model(model_path: str = None, root_path: str = None):
        if model_path is None:
            if root_path is None:
                raise ValueError("root_path is required if model_path is not provided.")
            model_path = os.path.join(root_path, f'static/models/inceptionv3.h5')


        return load_model(model_path)
    
    @staticmethod
    def load_model_from_google_drive(file_id: str, credentials_file: str = None):
        raise NotImplementedError("This method is under construction.")
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(credentials_file=credentials_file)
        if gauth.credentials is None:
            # Authenticate if credentials do not exist
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            # Refresh token if expired
            gauth.Refresh()
        else:
            # Authenticate using existing credentials
            gauth.Authorize()

        # Save the current credentials to a file
        gauth.SaveCredentialsFile("c.json")

        drive = GoogleDrive(gauth)

        # Fetch the model file by its file ID
        file = drive.CreateFile({'id': file_id})
        model_content = file.GetContentString()

        print(model_content[0:1000])
        return model_content

    @staticmethod
    def preprocess_image(image_path: str):
        # validate file path
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        img = load_img(image_path, target_size=(224, 224))
        img_array = img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        return preprocess_input(img_array)
    
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
    def save_image(image: FileStorage, root_path: str, folder_name: str = 'profile_pics', resize: bool = True):

        image_name = secrets.token_hex(8) + os.path.splitext(image.filename)[1]
        image_path = os.path.join(root_path, f'static/images/{folder_name}', image_name)

        if resize:
            # resize image
            output_size = (125, 125)
            resized_image = Image.open(image)
            resized_image.thumbnail(output_size)
            resized_image.save(image_path)
        else:
            image.save(image_path)

        return image_name


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
