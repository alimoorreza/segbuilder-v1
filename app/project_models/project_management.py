from ..resources.aws_resources import get_s3_client, get_s3_resource
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


class SB_project_image:
    def __init__(self,username,project,image_file):
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
        self.__s3_client = get_s3_client() 
        _, s3_bucket = get_s3_resource()
        self.__s3_bucket_name = s3_bucket.name

    def __load_file_from_s3(self,s3_path):
        try:
            obj = self.__s3_client.get_object(Bucket=self.__s3_bucket_name,Key=s3_path)
            data = obj['Body'].read()
            return data
        except Exception as e:
            logging.debug("Error occurred while reading the file from S3: %s", e)
            return None
        
    def __write_file_to_s3(self,s3_path,data):
        self.__s3_client.put_object(Bucket=self.__s3_bucket_name,Key=s3_path,Body=data)
        
    def __file_exists_in_s3(self,s3_path):
        try:
            #logging.debug("seeing if",s3_path,"exists")
            response = self.__s3_client.head_object(Bucket=self.__s3_bucket_name, Key=s3_path)
            #logging.debug("head object response:",response)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    def __read_image_from_s3(self, s3_path):
        # Download the image file in memory
        file_byte_string = self.__s3_client.get_object(Bucket=self.__s3_bucket_name, Key=s3_path)['Body'].read()

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
        compressed_data = self.__load_file_from_s3(self.__masks_path)
        #with open(self.__masks_path,'rb') as masks_file:
        #    compressed_data = masks_file.read()
        decompressed_pickle_data = gzip.decompress(compressed_data)
        data = pickle.loads(decompressed_pickle_data)       
        self.__masks = data["masks"]
        #need to make the segments back into numpy arrays instead of lists
        for idx in range(len(self.__masks)):
            self.__masks[idx]["segmentation"] = np.array(self.__masks[idx]["segmentation"])
            #print("MASK",idx)
            #print(self.__masks[idx])
        self.__labels = data["labels"]

    def get_filename(self):
        return self.__filename
        
    def has_masks(self):
        #return os.path.isfile(self.__masks_path)
        result = self.__file_exists_in_s3(self.__masks_path)
        return result
    
    def has_segmented_image(self):
        #return os.path.isfile(self.__segments_path)
        result = self.__file_exists_in_s3(self.__segments_path)
        return  result
    
    def get_segmented_image_path(self):
        return self.__segments_path
    
    def load_masks(self):
        if not self.__masks:
            self.__unpack_archive()
        return self.__masks
    
    def load_labels(self):
        if not self.__labels:
            self.__unpack_archive()
        return self.__labels
    
    def load_image(self):
        image = self.__read_image_from_s3(self.__image_path)
        #image = cv2.imread(self.__image_path)
        #image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image

    def load_segmented_image(self):
        image = self.__read_image_from_s3(self.__segments_path)
        #image = cv2.imread(self.__segments_path)
        #image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image

    def update_archive(self,old_mask_labels,new_masks,new_mask_labels):
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
        #with open(self.__masks_path,'wb') as archive_file:
        #    archive_file.write(compressed_pickle_data)
        self.__write_file_to_s3(self.__masks_path,compressed_pickle_data)

    def save_segmented_image(self,new_segmented_image):
        if new_segmented_image:
            base64_img_data = new_segmented_image.split(',')[1]
            img_bytes = base64.b64decode(base64_img_data)
            #with open(self.__segments_path,'wb') as segment_image_file:
            #    segment_image_file.write(img_bytes)
            self.__write_file_to_s3(self.__segments_path,img_bytes)

class SB_project:
    def __init__(self, username, project_name):
        logging.debug("SBDEBUG: creating SB_project for"+str(project_name))
        self.__username = username
        self.__project_name = project_name
        self.__images_dir_path = "images/"+self.__username+"/"+self.__project_name
        self.__segmented_images_dir_path = "segmented_images/"+self.__username+"/"+self.__project_name
        self.__s3_client = get_s3_client() 
        _, s3_bucket = get_s3_resource()
        self.__s3_bucket_name = s3_bucket.name

    def get_image_names(self):
        logging.debug("SBDEBUG: inside get_image_names")
        files = []
        logging.debug("SBDEBUG: about to connect to s3")
        paginator = self.__s3_client.get_paginator('list_objects_v2') 
        logging.debug("SBDEBUG: got the paginator")
        logging.debug("SBDEBUG: self.__s3_bucket_name: %s",self.__s3_bucket_name)
        result = paginator.paginate(Bucket=self.__s3_bucket_name, Prefix=self.__images_dir_path)
        for page in result:
            for obj in page.get('Contents', []):
                filename = obj['Key'][(len(self.__images_dir_path)+1):]
                files.append(filename)
        logging.debug("SBDEBUG: here are the images read from s3"+str(files))
        return files
        #return os.listdir(self.__images_dir_path)
    
    def get_cover_image_url(self):
        logging.debug("SBDEBUG: About to get the cover image for "+self.__project_name)
        cover_image = "assets/eyelogo.png"
        image_names = self.get_image_names()
        if len(image_names) > 0:
            try:
                cover_image = self.__s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': self.__s3_bucket_name,
                                                            'Key': self.__images_dir_path+"/"+image_names[0]},
                                                    ExpiresIn=3600)
            except NoCredentialsError as e:
                logging.error("SBDEBUG: NoCredentialsError")
                logging.error("%s",e)

        return cover_image
    
    def prepare_download(self,file_list,zipfilename):
        if os.path.exists("tmp/"+self.__username):
            shutil.rmtree("tmp/"+self.__username)
        if not os.path.exists("tmp/downloads"):
            os.makedirs("tmp/downloads")
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/images')
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/segmented_images')
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/image_masks')

        for filename in file_list:
            #strip out leading space
            if filename[0] == " ":
                filename = filename[1:]
            filename_plus_png = filename
            if len(filename) > 4 and filename[-4] == ".":
                filename_plus_png = filename[:-4]
            filename_plus_png += ".png"
            filename_plus_sgdbi = filename
            if len(filename) > 4 and filename[-4] == ".":
                filename_plus_sgbdi = filename[:-4]
            filename_plus_sgbdi += ".sgbdi"  
            try:
                self.__s3_client.download_file(self.__s3_bucket_name,self.__images_dir_path+"/"+filename,f'tmp/{self.__username}/{self.__project_name}/images/{filename}')
            except:
                logging.debug("couldn't download  %s",filename)
            try:
                self.__s3_client.download_file(self.__s3_bucket_name,self.__images_dir_path+"/"+filename,f'tmp/{self.__username}/{self.__project_name}/image_masks/{filename_plus_sgbdi}')
            except:
                logging.debug("couldn't download  %s",filename)
            try:
                self.__s3_client.download_file(self.__s3_bucket_name,self.__segmented_images_dir_path+"/"+filename_plus_png,f'tmp/{self.__username}/{self.__project_name}/segmented_images/{filename_plus_png}')
            except:
                logging.debug("couldn't download  %s",filename_plus_png)
            
        with zipfile.ZipFile("tmp/downloads/"+zipfilename,'w') as zipf:
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'images',filename)
                    zipf.write(filePath,arcname=archive_path)
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/image_masks"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'sgbdi',filename)
                    zipf.write(filePath,arcname=archive_path)
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/segmented_images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'masks',filename)
                    zipf.write(filePath,arcname=archive_path)

        return "tmp/downloads/"+zipfilename