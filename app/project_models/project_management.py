import os
import boto3
from botocore.exceptions import NoCredentialsError
import io
import numpy as np
from PIL import Image, ImageOps
import cv2
import gzip
import pickle
import logging
import botocore
import base64
import shutil
import zipfile

from ..resources import load_file, write_file, file_exists, serve_file, get_files_in_directory, file_download

class SB_project_image:
    """
    Class for managing images and associated masks.
    
    Attributes:
    - __username (str): The username of the user.
    - __project (str): The name of the project.
    - __filename (str): The filename of the image.
    - __file_prefix (str): The prefix of the image file (excluding extension).
    - __file_suffix (str): The suffix of the image file (extension).
    - __image_path (str): The path to the image file in file storage (either cloud or local).
    - __masks_path (str): The path to the masks file in file storage.
    - __segments_path (str): The path to the segmented image file in file storage.
    - __masks (list): The list of masks associated with the image.
    - __labels (list): The list of labels associated with the masks.
    - __segmented_image (numpy array): The segmented image array.
    """
    def __init__(self,username,project,image_file):
        """
        Initialize a new SB_project_image instance.
        
        :param username: The username of the user.
        :param project: The name of the project.
        :param image_file: The filename of the image.
        """
        self.__username = username
        self.__project = project
        self.__filename = image_file
        self.__file_prefix = image_file
        self.__file_suffix = ""
        if len(image_file) > 4 and (image_file[-4:] == ".jpg" or image_file[-4:] == ".png"):
            self.__file_prefix = image_file[:-4]
            self.__file_suffix = image_file[-4:]
        self.__image_path = "images/"+self.__username+"/"+self.__project+"/"+self.__filename
        self.__masks_path = "image_masks/"+self.__username+"/"+self.__project+"/"+self.__file_prefix+".sgbdi"
        self.__segments_path = "segmented_images/"+self.__username+"/"+self.__project+"/"+self.__file_prefix+".png"
        self.__masks = None
        self.__labels = None
        self.__segmented_image = None


    def __read_image(self, path):
        """
        Read an image from the given path and convert it to a NumPy array.
        
        :param path: The path to the image file.
        :return: The image as a NumPy array.
        """
        # Download the image file in memory
        file_byte_string = load_file(path)

        # Create a file-like object for the image file
        image_file = io.BytesIO(file_byte_string)

        # Open the image file with PIL, then convert it to a NumPy array
        image = Image.open(image_file)
        image = ImageOps.exif_transpose(image)
        image_array = np.array(image)

        # If the image is not RGB, convert it to RGB
        if image_array.shape[2] == 4:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        elif image_array.shape[2] == 1:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        #else:
        #    image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            
        return image_array

    def __unpack_archive(self):
        """
        Unpack the masks and labels from the compressed archive file.

        The .sgbdi files are archives, which are pickled dictionaries that have been gzipped
        """
        #compressed_data = self.__load_file_from_s3(self.__masks_path)
        compressed_data = load_file(self.__masks_path)
        #with open(self.__masks_path,'rb') as masks_file:
        #    compressed_data = masks_file.read()
        decompressed_pickle_data = gzip.decompress(compressed_data)
        data = pickle.loads(decompressed_pickle_data)       
        self.__masks = data["masks"]
        #need to make the segments back into numpy arrays instead of lists
        for idx in range(len(self.__masks)):
            self.__masks[idx]["segmentation"] = np.array(self.__masks[idx]["segmentation"])
        self.__labels = data["labels"]

    def get_filename(self):
        """
        Get the filename of the image.
        
        :return: The filename of the image.
        """
        return self.__filename
        
    def has_masks(self):
        """
        Check if the image has associated masks.
        
        :return: True if masks exist, False otherwise.
        """
        result = file_exists(self.__masks_path)
        return result
    
    def has_segmented_image(self):
        """
        Check if the image has associated masks.
        
        :return: True if masks exist, False otherwise.
        """
        result = file_exists(self.__segments_path)
        return  result
    
    def get_segmented_image_path(self):
        """
        Get the path to the segmented image.
        
        :return: The path to the segmented image.
        """
        return self.__segments_path
    
    def load_masks(self):
        """
        Get the path to the segmented image.
        
        :return: The path to the segmented image.
        """
        if not self.__masks:
            self.__unpack_archive()
        return self.__masks
    
    def load_labels(self):
        """
        Load the labels associated with the masks.
        
        :return: The list of labels.
        """
        if not self.__labels:
            self.__unpack_archive()
        return self.__labels
    
    def load_image(self):
        """
        Load the image as a NumPy array.
        
        :return: The image as a NumPy array.
        """
        image = self.__read_image(self.__image_path)
        return image

    def load_segmented_image(self):
        """
        Load the segmented image as a NumPy array.
        
        :return: The segmented image as a NumPy array.
        """
        image = self.__read_image(self.__segments_path)
        return image

    def update_archive(self,old_mask_labels,new_masks,new_mask_labels):
        """
        Update the archive with new and old masks and labels.
        
        :param old_mask_labels: The list of old mask labels.
        :param new_masks: The list of new masks.
        :param new_mask_labels: The list of new mask labels.
        """
        if not new_masks:
            new_masks = []
            new_mask_labels = []
        old_masks = self.load_masks()
        logging.debug("length of new and old masks: %s, %s",len(new_masks),len(old_masks))
        combined_masks = new_masks+old_masks
        combined_labels = new_mask_labels+old_mask_labels
        filtered_masks = [combined_masks[i] for i in range(len(combined_masks)) if combined_labels[i] != "DELETE" ]
        filtered_labels = [combined_labels[i] for i in range(len(combined_masks)) if combined_labels[i] != "DELETE" ]
        savable_data = {"image": self.load_image(), "masks": filtered_masks, "labels": list(filtered_labels)}
        pickle_data = pickle.dumps(savable_data)
        compressed_pickle_data = gzip.compress(pickle_data)
        write_file(self.__masks_path,compressed_pickle_data)

    def save_segmented_image(self,new_segmented_image):
        """
        Save the new segmented image.
        
        :param new_segmented_image: The new segmented image in base64 format.
        """
        if new_segmented_image:
            base64_img_data = new_segmented_image.split(',')[1]
            img_bytes = base64.b64decode(base64_img_data)
            write_file(self.__segments_path,img_bytes)

class SB_project:
    """
    Class for managing projects for a given user, including images, image masks, and segmented images according to label-color schemes.

    Attributes:
    - __username (str): The username of the user.
    - __project_name (str): The name of the project.
    - __images_dir_path (str): The directory path for the project's images.
    - __segmented_images_dir_path (str): The directory path for the project's segmented images.
    """
    
    def __init__(self, username, project_name):
        """
        Initialize a new SB_project instance.

        :param username: The username of the user.
        :param project_name: The name of the project.
        """
        logging.debug("SBDEBUG: creating SB_project for"+str(project_name))
        self.__username = username
        self.__project_name = project_name
        self.__images_dir_path = "images/"+self.__username+"/"+self.__project_name
        self.__segmented_images_dir_path = "segmented_images/"+self.__username+"/"+self.__project_name

    def get_image_names(self):
        """
        Get the names of the images in the project's image directory.

        :return: A list of image filenames.
        """
        return get_files_in_directory(self.__images_dir_path)
    
    def get_cover_image_url(self):
        """
        Get the URL for the project's cover image.

        If the project has images, the first image is used as the cover image. 
        Otherwise, a default logo image is used.

        :return: The URL of the cover image.
        """
        logging.debug("SBDEBUG: About to get the cover image for "+self.__project_name)
        cover_image = "assets/eyelogo.png"
        image_names = get_files_in_directory(self.__images_dir_path)

        if len(image_names) > 0:
            img_path = os.path.join(self.__images_dir_path,image_names[0])
            cover_image = serve_file(img_path)

        return cover_image
    
    def prepare_download(self,file_list,zipfilename):
        """
        Prepare the project files for download by creating a ZIP archive.

        The method creates temporary directories for the project files, downloads the specified files,
        and then archives them into a ZIP file.

        :param file_list: A list of filenames to be included in the download.
        :param zipfilename: The name of the ZIP file to create.
        :return: The path to the created ZIP file.
        """
        # Remove the user's temporary directory if it exists
        if os.path.exists("tmp/"+self.__username):
            shutil.rmtree("tmp/"+self.__username)

        # Create necessary directories for downloading and archiving files
        if not os.path.exists("tmp/downloads"):
            os.makedirs("tmp/downloads")
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/images')
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/segmented_images')
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/image_masks')

        # Download each file in the file list
        for filename in file_list:
            #strip out leading space
            if filename[0] == " ":
                filename = filename[1:]
            filename_plus_png = filename

            # figure out the name that the segmented image will have - it's the base filename plus png (even if the original was a jpg)
            if len(filename) > 4 and filename[-4] == ".":
                filename_plus_png = filename[:-4]
            filename_plus_png += ".png"

            # figure out the name of the SegBuilder archive file (.sgbdi) - it's the base file name plus .sgbdi
            filename_plus_sgbdi = filename
            if len(filename) > 4 and filename[-4] == ".":
                filename_plus_sgbdi = filename[:-4]
            filename_plus_sgbdi += ".sgbdi"  


            # download the original image file
            try:
                file_download(self.__images_dir_path+"/"+filename,f'tmp/{self.__username}/{self.__project_name}/images/{filename}')
            except:
                logging.debug("couldn't download  %s",filename)

            # download the image masks archive (.sgbdi file)
            try:
                file_download(self.__images_dir_path+"/"+filename,f'tmp/{self.__username}/{self.__project_name}/image_masks/{filename_plus_sgbdi}')
            except:
                logging.debug("couldn't download  %s",filename)

            # download the segmented image corresponding to this image
            try:
                file_download(self.__segmented_images_dir_path+"/"+filename_plus_png,f'tmp/{self.__username}/{self.__project_name}/segmented_images/{filename_plus_png}')
            except:
                logging.debug("couldn't download  %s",filename_plus_png)
            
        # Create ZIP archive
        with zipfile.ZipFile("tmp/downloads/"+zipfilename,'w') as zipf:
            # put original images in the images/ subdirectory
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'images',filename)
                    zipf.write(filePath,arcname=archive_path)
            # put SegBuilder masks archives in the image_masks/ subdirectory
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/image_masks"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'sgbdi',filename)
                    zipf.write(filePath,arcname=archive_path)
            # put segmented images in the segmented_images/ subdirectory
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/segmented_images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'masks',filename)
                    zipf.write(filePath,arcname=archive_path)

        return "tmp/downloads/"+zipfilename