from flask import Flask
import flask
from flask import Flask, request, render_template, redirect, session
from flask_dynamodb_sessions import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, ctx, no_update, callback_context, exceptions
import os
import boto3
import botocore
from botocore.exceptions import ClientError, NoCredentialsError
from dash.dependencies import Input, Output, State, ALL, MATCH
from PIL import Image, ImageOps
import cv2
import base64
import numpy as np
import pickle
import gzip
import io
import json
import plotly.express as px
import dash_daq as daq
import plotly.graph_objs as go
from matplotlib.path import Path
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import datetime
import re
import uuid
import threading
import logging
import zipfile
import shutil
import simplejson as json

os.environ["AWS_DEFAULT_REGION"] = "us-east-2"

dynamodb = boto3.resource('dynamodb',region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')
s3_resource = boto3.resource('s3',region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')
S3_BUCKET_NAME = 'segbuilder'
s3_bucket = s3_resource.Bucket(S3_BUCKET_NAME)


# 'application' must be used if deploying on ElasticBeanstalk
application = Flask(__name__)
application.secret_key = 'development-server-secret-key-TODO!!-fix-this-for-production'
application.config["SESSION_COOKIE_SECURE"] = False


Session(application)

def debug_print(*args, **kwargs):
    DEBUG = True
    if DEBUG:
        print(args)


# Flask-Login manager
login_manager = LoginManager()
login_manager.init_app(application)



IMG_HEIGHT = 400
IMG_WIDTH = 250
CANVAS_WIDTH = 600


#CANVAS_HEIGHT = 1000
#LABEL_OPTIONS = [n['name'] for n in LABEL_COLORS]+["DELETE"]

# #SAM stuff
# SAM_CHECKPOINT = "s3://segbuilder/_models/sam_vit_h_4b8939.pth"
# #check if we're running locally
# if __name__ == "__main__": 
#     SAM_CHECKPOINT = "../models/sam_vit_h_4b8939.pth"
# MODEL_TYPE     = "vit_h"
# DEVICE = "cpu"
# SAM = sam_model_registry[MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
# SAM.to(device=DEVICE)
# MASK_GENERATOR = SamAutomaticMaskGenerator(model=SAM)
# EXECUTOR = concurrent.futures.ProcessPoolExecutor(max_workers=5)

# def generate_sgbdi_file(img, username, selected_project, filename):
#     try:
#         debug_print("MASK GENERATION DEBUG: in generate_sgbdi_file")
#         start = datetime.datetime.now()
#         masks = MASK_GENERATOR.generate(img)
#         end = datetime.datetime.now()
#         debug_print("MASK GENERATION DEBUG: done generating masks, run time",end-start)
#         masks = sorted(masks, key=(lambda x: x['area']), reverse=True)
#         labels = ["unlabeled"]*len(masks)
#         data = {"image": img, "masks": masks, "labels": labels}
#         pickle_data = pickle.dumps(data)
#         compressed_pickle_data = gzip.compress(pickle_data)
#         sgbdi_filename = filename[:-4]+".sgbdi"
#         filename_on_s3 = "image_masks/"+username+"/"+selected_project+"/"+sgbdi_filename
#         s3_bucket.put_object(Key=filename_on_s3, Body=compressed_pickle_data)
#     except Exception as e:
#         debug_print(f"Exception occurred in generate_sgbdi_file: {e}")



def create_mask_from_paths(path_coordinates, img_shape):
    #debug_print("Path coordinates:", path_coordinates)
    #debug_print("Image shape:",img_shape)
    height, width, _ = img_shape
    #y, x = np.mgrid[:height, :width]
    #points = np.vstack((x.ravel(), y.ravel())).T
    x, y = np.meshgrid(np.arange(width),np.arange(height))
    #debug_print("x",x)
    x, y = x.flatten(), y.flatten()
    #debug_print("x flat",x)
    points = np.vstack((x,y)).T
    #debug_print("points",points)

    mask = np.zeros((height, width), dtype=bool)
    for path_coords in path_coordinates:
        path = Path(path_coords)
        mask |= path.contains_points(points).reshape(height, width)

    #debug_print('mask,',mask)
    #debug_print("num trues",mask.sum())

    return mask

def encode_img_for_display(cv2rgbimg):
    _, buffer = cv2.imencode('.png', cv2rgbimg)
    #
    encoded_image = base64.b64encode(buffer).decode('utf-8')
    return encoded_image

def apply_mask_to_image(image, mask):
    #debug_print(mask)
    # Ensure the mask is a boolean array
    mask = mask.astype(bool)

    # Create an empty image with the same dimensions as the original image
    masked_image = np.zeros_like(image)

    # Apply the mask to the image
    masked_image[mask] = image[mask]

    return masked_image


def get_cv2_image(filename):
    img = cv2.imread(filename)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def create_mask_cards(img, masks, labels, label_options = ["unlabeled"], new_masks=False, index_offset = 0):
    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    id_type = "label-dropdown"
    front_button_id_type = "front-button"
    delete_button_id_type = "delete-button"
    card_id_type = "mask-card"
    if new_masks:
        id_type = "new-label-dropdown"
        front_button_id_type = "new-front-button"
        delete_button_id_type = "new-delete-button"
        card_id_type = "new-mask-card"
    card_list = []
    print("DEBUG: (create_mask_cards)")
    print("\tlabels:",labels)
    print("\tlen(labels), len(masks):",len(labels),len(masks))
    #if there aren't enough labels for all the masks,
    #we will just copy the last label and use it for the rest of the masks
    #only will work if there is at least one label
    if len(labels) < len(masks):
        labels = labels+([labels[-1]]*(len(masks)-len(labels)))
    for idx in range(len(masks)):
        label_idx = idx+index_offset
        curr_card = html.Div([
            html.Img(src='data:image/png;base64,{}'.format(encode_img_for_display(apply_mask_to_image(image,masks[idx]["segmentation"]))),width=IMG_WIDTH),
            dbc.Button(html.I(className="bi bi-box-arrow-in-up-left"),color="secondary",id={'type':front_button_id_type,'index':label_idx},style={"float":"left"}),
            dbc.Button(html.I(className="bi bi-backspace"),color="danger",id={'type':delete_button_id_type,'index':label_idx},style={"float":"left"}),
            dcc.Dropdown(options=label_options,value=labels[idx],id={'type':id_type,'index':label_idx},style={"float":"left","width":(IMG_WIDTH-91)})
        ],style={"width":(IMG_WIDTH+10)},id={'type':card_id_type,'index':label_idx},className="float-child")
        card_list.append(curr_card)
    
    
    return card_list


def add_meta_info_to_masks(flat_masks):
    meta_masks = []
    for mask_num in range(len(flat_masks)):
        curr_meta_mask = {}
        curr_meta_mask["segmentation"] = flat_masks[mask_num]
        #!! TODO: add more meta info
        meta_masks.append(curr_meta_mask)
    return meta_masks

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2 ,4)]

"""
def populate_projects(username):
    project_directories = []
    #rootdir = "projects"
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2') 
    result = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=username+"/",Delimiter="/")
    for prefix in result.search('CommonPrefixes'):
        debug_print("prefix",prefix)
        foldername = prefix.get('Prefix')[len(username)+1:-1]
        project_directories.append(foldername)

    #for file in os.listdir(rootdir):
    #    d = os.path.join(rootdir,file)
    #    if os.path.isdir(d):
    #        debug_print(file,type(file))
    #        project_directories.append(file)
    return project_directories
"""




def populate_project_cards(username):
    debug_print("SBDEBUG: inside populate_project_cards")
    project_cards = []
    curr_projects = []

    #s3 = boto3.client('s3')
    #paginator = s3.get_paginator('list_objects_v2') 
    #result = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=username+"/",Delimiter="/")
    projects_table = dynamodb.Table("projects")
    curr_projects_response = projects_table.get_item(Key={"username":username})
    debug_print("In populate_project_cards: curr_projects_response",curr_projects_response)
    if "Item" in curr_projects_response:
        curr_projects = curr_projects_response["Item"]["projects"]
    #for prefix in result.search('CommonPrefixes'):
    for proj in curr_projects:
        #debug_print("prefix",prefix)
        #foldername = prefix.get('Prefix')[len(username)+1:-1]
        sb_project = SB_project(username,proj)
        debug_print("SBDEBUG: about to create a project card")
        curr_card = html.Div(id={'type':"project-card",'index':proj},children=dbc.Card([
            dbc.CardImg(src=sb_project.get_cover_image_url(),style={"height":"14rem"}),
            dbc.CardBody(html.H4(proj,className="card-title"),style={"textAlign":"center"})
        ],style={"height":"18rem","width": "18rem"}),style={"float":"left","paddingLeft":"20px"})
        debug_print("SBDEBUG: finished createing project card")
        project_cards.append(curr_card)

    return project_cards


def make_composite_image(image,mask_image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
    gray_background_image = np.where(mask_image > 0, mask_image, gray_image)
    mask_composite_image = np.zeros_like(image)
    mask_composite_image = cv2.addWeighted(gray_background_image,0.95,mask_image,0.05,0)
    mask_composite_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_composite_image, cv2.COLOR_BGR2RGB)))
    display_mask_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_image, cv2.COLOR_BGR2RGB)))
    return mask_composite_image, display_mask_image




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
        self.__s3_client = boto3.client('s3',region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')

    def __load_file_from_s3(self,s3_path):
        try:
            obj = self.__s3_client.get_object(Bucket=S3_BUCKET_NAME,Key=s3_path)
            data = obj['Body'].read()
            return data
        except Exception as e:
            debug_print("Error occurred while reading the file from S3:", e)
            return None
        
    def __write_file_to_s3(self,s3_path,data):
        self.__s3_client.put_object(Bucket=S3_BUCKET_NAME,Key=s3_path,Body=data)
        
    def __file_exists_in_s3(self,s3_path):
        try:
            #debug_print("seeing if",s3_path,"exists")
            response = self.__s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_path)
            #debug_print("head object response:",response)
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
        file_byte_string = self.__s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_path)['Body'].read()

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
        debug_print("length of new and old masks:",len(new_masks),len(old_masks))
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
        debug_print("SBDEBUG: creating SB_project for"+str(project_name))
        self.__username = username
        self.__project_name = project_name
        self.__images_dir_path = "images/"+self.__username+"/"+self.__project_name
        self.__segmented_images_dir_path = "segmented_images/"+self.__username+"/"+self.__project_name
        self.__s3_client = boto3.client('s3',region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')

    def get_image_names(self):
        debug_print("SBDEBUG: inside get_image_names")
        files = []
        debug_print("SBDEBUG: about to connect to s3")
        paginator = self.__s3_client.get_paginator('list_objects_v2') 
        debug_print("SBDEBUG: got the paginator")
        result = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=self.__images_dir_path)
        for page in result:
            for obj in page.get('Contents', []):
                filename = obj['Key'][(len(self.__images_dir_path)+1):]
                files.append(filename)
        debug_print("SBDEBUG: here are the images read from s3"+str(files))
        return files
        #return os.listdir(self.__images_dir_path)
    
    def get_cover_image_url(self):
        debug_print("SBDEBUG: About to get the cover image for "+self.__project_name)
        cover_image = "assets/eyelogo.png"
        image_names = self.get_image_names()
        if len(image_names) > 0:
            try:
                cover_image = self.__s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': S3_BUCKET_NAME,
                                                            'Key': self.__images_dir_path+"/"+image_names[0]},
                                                    ExpiresIn=3600)
            except NoCredentialsError as e:
                logging.error("SBDEBUG: NoCredentialsError")
                logging.error(e)

        return cover_image
    
    def prepare_download(self,file_list,zipfilename):
        if os.path.exists("tmp/"+self.__username):
            shutil.rmtree("tmp/"+self.__username)
        if not os.path.exists("tmp/downloads"):
            os.makedirs("tmp/downloads")
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/images')
        os.makedirs("tmp/"+self.__username+'/'+self.__project_name+'/segmented_images')

        for filename in file_list:
            #strip out leading space
            if filename[0] == " ":
                filename = filename[1:]
            filename_plus_png = filename
            if len(filename) > 4 and filename[-4] == ".":
                filename_plus_png = filename[:-4]
            filename_plus_png += ".png"
            try:
                self.__s3_client.download_file(S3_BUCKET_NAME,self.__images_dir_path+"/"+filename,f'tmp/{self.__username}/{self.__project_name}/images/{filename}')
            except:
                debug_print("couldn't download",filename)
            try:
                self.__s3_client.download_file(S3_BUCKET_NAME,self.__segmented_images_dir_path+"/"+filename_plus_png,f'tmp/{self.__username}/{self.__project_name}/segmented_images/{filename_plus_png}')
            except:
                debug_print("couldn't download",filename_plus_png)
            
        with zipfile.ZipFile("tmp/downloads/"+zipfilename,'w') as zipf:
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'images',filename)
                    zipf.write(filePath,arcname=archive_path)
            for foldername, subfolders,filenames in os.walk(f"tmp/{self.__username}/{self.__project_name}/segmented_images"):
                for filename in filenames:
                    filePath = os.path.join(foldername,filename)
                    archive_path = os.path.join(self.__project_name,'masks',filename)
                    zipf.write(filePath,arcname=archive_path)

        return "tmp/downloads/"+zipfilename

def populate_files(username,project_name):
    image_list = []
    project_object = SB_project(username,project_name)
    filelist = project_object.get_image_names()
    
    for file_idx in range(len(filelist)):
        file = SB_project_image(username,project_name,filelist[file_idx])
        item_color = None
        if file.has_masks():
            item_color = "primary"
        if file.has_segmented_image():
            item_color = "success"
        image_list.append(dbc.ListGroupItem(dbc.Row([
                dbc.Col(dcc.Checklist(options=[""],value=[],id={'type':"file-item-checklist",'index':file.get_filename()}),width="auto"),
                dbc.Col(html.Div(file.get_filename(),id={'type':"file-item",'index':file.get_filename()})),
            ]),color=item_color)
        )
    
    
    return image_list

# Dash app
app = Dash(__name__, server=application, title="SegBuilder", url_base_pathname='/segbuilder/',external_stylesheets=[dbc.themes.BOOTSTRAP,dbc.icons.BOOTSTRAP])
#app = Dash(__name__, server=application, title="SegBuilder",external_stylesheets=[dbc.themes.BOOTSTRAP,dbc.icons.BOOTSTRAP])


class User(UserMixin):
    def __init__(self, username, password):
        self.id = username
        self.password = password #generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

@login_manager.user_loader
def load_user(username,get_response_item=False):
    debug_print("LOADUSER: username,",username,type(username))
    users_table = dynamodb.Table('users')
    debug_print("LOADUSER: users table from dynamo,",users_table)
    try:
        response = users_table.get_item(
           Key={
                'username': username
            }
        )

        debug_print("LOADUSER: response,",response)
    except ClientError as e:
        debug_print(e.response['Error']['Message'])
        return None
    else:
        if 'Item' in response:
            if get_response_item:
                return response["Item"]
            else:
                user_data = response['Item']
                return User(user_data['username'], user_data['password'])
        else:
            return None
    #return users.get(username)


def change_password_in_db(username, new_password):
    users_table = dynamodb.Table('users')
    new_password_hashed = generate_password_hash(new_password)
    try:
        users_table.update_item(
            Key={
                'username': username
            },
            UpdateExpression='SET password = :val1',
            ExpressionAttributeValues={
                ':val1': new_password_hashed
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

    return True

"""
@server.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = load_user(username)
        if user and user.check_password(password):
            login_user(user)
            # Redirect to Dash app
            return redirect('/segbuilder/')
        else:
            return 'Invalid username or password'
    else:
        return render_template('login.html')
"""

# @app.server.route('/logout')
# @login_required
# def logout():
#     #logout_user()
#     debug_print("got to logout callback")
#     session_id = session.get('session_id')

#     #!!TODO: add error handling in case we lose connection to DynamoDB
#     # Remove the session data from DynamoDB
#     if session_id:
#         sessions_table = dynamodb.Table('sessions')
#         sessions_table.delete_item(Key={'session_id': session_id})
#     session.clear()
#     return redirect('/')
 

# @app.server.route('/segbuilder/')
# @login_required
# def render_dashboard():
#     return flask.redirect('/dash/')

login_layout = html.Div([
    #dcc.Location(id='url_login', refresh=True),
    dbc.Container([
        dbc.Card(
            [
                    dbc.FormText('Invalid username or password.',color="danger",id="invalid-password-message",style={'display':"none"}),
                    dbc.Label('Username'),
                    dbc.Input(id='login-username', placeholder='Enter username'),
                    dbc.Label('Password'),
                    dbc.Input(id='login-password', type='password', placeholder='Enter password'),
                    html.Br(),
                    dbc.Button('Login', id='login-button', color='primary')

            ],
            body=True,
            class_name="p-3"
        ),
    ],class_name='mt-5 d-inline-flex justify-content-center')
])


segbuilder_layout = html.Div(children = [
    dbc.Tabs(id="tabs", active_tab="projects_tab", children = [
        dbc.Tab(tab_id="projects_tab",label="Projects",children=[
            dcc.Markdown("## Select project"),
            #dcc.Dropdown(id="project-select-dropdown",options=[]),
            html.Div(id="new-project-card",
                     children=dbc.Card([
                        #html.H4("Create Project",style={"textAlign":"center"}),
                        html.H1("+",style={"textAlign":"center","fontSize":"10rem","verticalAlign":"middle"}),
                        #dbc.Input(id="new-project-name-input",value="new_project_name",type="text")
            ],style={"height":"18rem","width": "18rem"}),style={"float":"left","paddingLeft":"20px"}),
            html.Div(id="project-cards",children=[]),
            dbc.Modal(id="create-project-modal",is_open=False, children=[
                dbc.ModalHeader(dbc.ModalTitle("Create new project")),
                dbc.ModalBody([
                    dbc.Label("Project name (no spaces)"),
                    dbc.Input(type="text",id="create-project-name-input"),
                    html.Div(dbc.FormText("Project names must start with a letter and contain only letters, numbers, and underscores.",color="danger"),id="create-new-project-name-message",style={"display":"none"})
                ]),
                dbc.ModalFooter(
                    dbc.Button("Create",id="create-project-button",color="primary")
                )
            ])
        ]),
        dbc.Tab(tab_id="classes_tab",label="Classes",children=[
            html.Br(),
            html.H3(id="project-name-display-on-classes"),
            html.Br(),
            dbc.Row([
                dbc.Col([dbc.Button("Download Label Color Scheme",id="download-label-color-scheme-button"),
                    dcc.Download(id='label-color-scheme-download')
            ],align="start",width="auto"),
                dbc.Col(dcc.Upload(id="label-color-scheme-upload",multiple=False,children=[
                        'Upload Label Color Scheme File',
                    ],
                    style={
                    'width': '33%',
                    'height': '36px',
                    # 'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'left-margin': '10px'
                    },
                ),align="start"),
            ]),
            html.Br(),
            dbc.Form(dbc.Row([
                dbc.Label("New Class label",width="auto"),
                dbc.Col(
                    dbc.Input(id="class-label-input",placeholder="Enter label for a new class"),
                    className="me-3",
                    width=4
                ),  
                dbc.Label("Color",width="auto"),
                dbc.Col(
                    dbc.Input(
                        type="color",
                        id="class-colorpicker",
                        value="#000000",
                        style={"width": 80, "height": 40},
                    ),width=2
                ),
                dbc.Col(dbc.Button("Submit", color="primary",id="new-class-label-button"), width="auto"),       
            ],className="g-2"),style={"marginLeft": "15px","width":"50rem"}),
            html.Br(),
            html.Div(id="label-color-map-display")
        ]),
        dbc.Tab(tab_id = "files_tab",label="Files",children=[
            dbc.Spinner(html.H3(id="project-name-display-on-files"),color="primary"),
            dcc.Upload(id="file-uploader",multiple=True,children=[
                'Drag and Drop or Select Image File'
            ],
            style={
            'width': '50%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
            },
        ),
        dbc.Button(html.I(className="bi bi-arrow-repeat"),id="refresh-button",color="primary"),
        dbc.Button(dbc.Spinner("Download"),id="download-button",color="primary"),
        html.Div(dbc.Spinner(dcc.Download(id="download-zipfile"),color="primary")),
        # dbc.Modal([
        #     dbc.ModalBody("The file is ready."),
        #     dbc.ModalFooter([
        #         dbc.Button("Download",id="download-download-modal",download="files.zip", className="ms-auto", n_clicks=0),
        #         dbc.Button("Close", id="close-download-modal", className="ms-auto", n_clicks=0)
        #         ]),
        # ],id = "download-modal",is_open=False,),
        dcc.Checklist(options=[" Select all"],value=[],id='select-all-checklist'),
        dbc.Toast(id="upload-notify",header="File uploaded",dismissable=True,is_open=False,style={"position": "fixed", "top": 66, "right": 10},),
        dbc.ListGroup(id="file-list-group",children=[]),
        ]),
        dbc.Tab(tab_id = "annotate_tab",label="Annotate",children=[
            html.H3(id="filename-display"),
            dbc.Row([
                dbc.Col([
                        dcc.Graph(id="graph-draw",config={"modeBarButtonsToAdd": ["drawclosedpath","eraseshape"], "displaylogo":False},style={"width":"700px"}),],align="center"), #"drawcircle","drawopenpath",
                dbc.Col(dbc.Spinner([
                    html.Img(src="",height=IMG_HEIGHT,id="mask-composite-image"),
                    html.Img(src="",height=IMG_HEIGHT,id="mask-image")
                ],color="primary"),align="center"), 
            ]),
            html.Br(),
            html.Div([
                dbc.Button("Generate Composite Mask Image",id="generate-composite-image-button",style={"marginLeft": "15px"}),
                dbc.Button("Generate Manual Mask",id="generate-manual-mask-button",style={"marginLeft": "15px"}),
                dbc.Button("Save",id="save-button",style={"marginLeft": "15px"}),
                dbc.Toast(id="save-notify",header="File saved",dismissable=True,is_open=False,style={"position": "fixed", "top": 66, "right": 10},)
            ]),
            html.Br(),
            dbc.Spinner([html.Div(children=[],id="new-mask-display")],color="primary"),
            html.Div(children=[],id="mask-display",className="float-container")
        ]),
    ]),
    dcc.Store(id='mask-store'),
    dcc.Store(id="new-mask-store"),
    #dcc.Store(id='image-store'),
    dcc.Store(id="drawings-store"),
    dcc.Store(id='closed-paths-store'),
    dcc.Store(id="selected-project"),
    dcc.Store(id="selected-image"),
    dcc.Store(id="mask-card-move-to-front"),
    dcc.Store(id="mask-move-to-front"),
    dcc.Store(id="new-project-has-been-created"),
    #dcc.Store(id='zipfile-store'),
])

password_change_modal = modal = dbc.Modal(
    [
        dbc.ModalHeader("Change Password"),
        dbc.ModalBody(
            dbc.Form(
                [
                    html.Div(
                        [
                            dbc.Label("Current Password", className="mr-2"),
                            dbc.Input(type="password", id="current-password"),
                        ],
                        className="mr-3",
                    ),
                    html.Div(
                        [
                            dbc.Label("New Password", className="mr-2"),
                            dbc.Input(type="password", id="new-password"),
                        ],
                        className="mr-3",
                    ),
                    html.Div(
                        [
                            dbc.Label("Confirm New Password", className="mr-2"),
                            dbc.Input(type="password", id="confirm-password"),
                        ],
                        className="mr-3",
                    ),
                    dbc.FormText('',color="danger",id="change-password-message"),
                ]
            )
        ),
        dbc.ModalFooter(
            dbc.Button("Change Password", id="change-password-button", className="ml-auto")
        ),
    ],
    id="password-modal",is_open=False
)

app.layout = html.Div([
    #dcc.Store(id='session', storage_type='session'),  # Add this line
    #dcc.Location(id='url', refresh=False),
    dbc.Row([
        dbc.Col(html.Img(src="assets/eyelogo.png",height=100),width='auto'),
        dbc.Col(children = [
            html.H1(children="SegBuilder"),
            html.H4(children="Machine-Assisted Semantic Segmentation Annotation"),
        ]),
        
        dbc.Col(children=[
            html.H6("User: None ",id="username-display"),
            dbc.DropdownMenu([
                dbc.DropdownMenuItem("Change Password",id="initiate-change-password-button",n_clicks=0),
                dbc.DropdownMenuItem("Logout",id="logout-button",n_clicks=0),
             ],label=(html.I(className="bi bi-person-lines-fill"))),
        ],
        style={"textAlign":"right","paddingRight":"30px","paddingTop":"20px"})
    ]),
    password_change_modal,
    dbc.Spinner(html.Div(login_layout,id='login-content',style={"display":"block"}),color="primary"),
    html.Div(segbuilder_layout,id='main-content',style={"display":"none"})
])

# def get_user_from_session(session_data):
#     if session_data is not None:
#         session_id = session_data.get("session_id")
#         if session_id is not None:
#             user_data = session.get(session_id)
#             if user_data is not None:
#                 username = user_data.get("username")
#                 return username
#     return None



def get_label_options(username,project):
    classes_table = dynamodb.Table("project-classes")
    classes_list = classes_table.get_item(Key={"username-projectname":username+"-"+project})["Item"]["classes"]
    debug_print("classes_list",classes_list)
    label_options = [n['name'] for n in classes_list]
    return label_options

def get_label_colors_dict(username,project):
    label_colors_dict = {}
    classes_table = dynamodb.Table("project-classes")
    classes_list = classes_table.get_item(Key={"username-projectname":username+"-"+project})["Item"]["classes"]
    for entry in classes_list:
        label_colors_dict[entry["name"]] = tuple(entry["color"])
    return label_colors_dict


def update_last_activity(session_id):
    sessions_table = dynamodb.Table('sessions')

    sessions_table.update_item(
        Key={'session_id': session_id},
        UpdateExpression="set last_activity = :t",
        ExpressionAttributeValues={
            ':t': datetime.datetime.now().isoformat()
        }
    )

# def get_user_from_session():
#     # Get session_id from the session
#     debug_print("SBDEBUG: in get_user_from_session")
#     session_id = session.get('session_id')
#     debug_print("SBDEBUG: in get_user_from_session, session_id",session_id)
#     if session_id is not None:
#         # Retrieve the associated username from DynamoDB
#         sessions_table = dynamodb.Table('sessions')
#         response = sessions_table.get_item(Key={'session_id': session_id})
#         debug_print("SBDEBUG: in get_user_from_session, response from sessions table:",response)

#         # Extract the username from the response if it exists
#         if 'Item' in response:
#             username = response['Item'].get('username')
#             debug_print("SBDEBUG: in get_user_from_session, about to generate new thread")
#             # Update the 'last_activity' timestamp for this session asynchronously
#             threading.Thread(target=update_last_activity, args=(session_id,)).start()
#             debug_print("SBDEBUG: in get_user_from_session, about to return username",username)
#             return username
#     return None

def get_user_from_session():
    # Get username from the session
    debug_print("SBDEBUG: in get_user_from_session")
    debug_print("***********Entire Session***************")
    debug_print(session)
    debug_print("**************************")
    debug_print(dict(session))
    debug_print("**************************")
    username = session.get('username')
    #username = session['username']
    debug_print("SBDEBUG: in get_user_from_session, about to return username",username)
    # If the session does not exist or has expired, username will be None.
    # No need to manually check DynamoDB because Flask-DynamoDB-SessionStore
    # takes care of that.

    return username


@app.callback(
    Output('label-color-scheme-download',"data"),
    Input("download-label-color-scheme-button","n_clicks"),
    State("selected-project","data"),
    prevent_initial_callback=True
)
def download_label_color_scheme_file(n,project_name):
    username = get_user_from_session()
    if n:
        classes_table = dynamodb.Table("project-classes")
        label_records = classes_table.get_item(Key={'username-projectname':username+"-"+project_name})["Item"]["classes"]
        return dict(content=json.dumps(label_records),filename=project_name+".json")
    return no_update

@app.callback(
    Output("password-modal", "is_open"),
    Output("change-password-message","children"),
    Input("change-password-button", "n_clicks"),
    Input("initiate-change-password-button","n_clicks"),
    State("current-password", "value"),
    State("new-password", "value"),
    State("confirm-password", "value"),
    prevent_initial_callback = True
)
def update_password(change_n, initiate_n, current_password, new_password, confirm_password):
    username = get_user_from_session()
    if callback_context.triggered_id == "initiate-change-password-button" and initiate_n and initiate_n > 0:
        return True, ""
    elif callback_context.triggered_id == "change-password-button" and change_n and change_n > 0:
        user_data = load_user(username,get_response_item=True)  # replace 'testuser' with actual username
        if user_data and check_password_hash(user_data['password'], current_password):
            if new_password != confirm_password:
                return no_update, "passwords do not match"
            else:
                if change_password_in_db(username, new_password):  # replace 'testuser' with actual username
                    return False, ""
                else:
                    return True, "Error: failed to update password"
        else:
            return no_update, "invalid password"
    return no_update, "error"

@app.callback(
    Output('download-zipfile','data'),
    Input("download-button","n_clicks"),
    State({'type': 'file-item-checklist', 'index': ALL}, 'value'),
    State({'type': 'file-item', 'index': ALL}, 'children'),
    State('selected-project','data'),
    prevent_initial_call = True
)
def initiate_download(n,filename_checklist_values,filenames,project_name):
    debug_print("DOWNLOADDEBUG: in initiate_download, nclicks:",n)
    debug_print("DOWNLOADDEBUG: filename_checklist_values:",filename_checklist_values)
    debug_print("DOWNLOADDEBUG: filenames:",filenames)
    username = get_user_from_session()
    if not username:
        raise PreventUpdate
    download_files = []
    for idx in range(len(filename_checklist_values)):
        if filename_checklist_values[idx] != []:
            download_files.append(filenames[idx])
    #download_files = [filename for filename in filenames if file != []]
    debug_print("DOWNLOADDEBUG: download_files",download_files)
    project = SB_project(username,project_name)
    unique_filename = str(uuid.uuid4()) + '.zip'
    zipfile_path = project.prepare_download(download_files,unique_filename)
    debug_print("DOWNLOADDEBUG: zip created")
    try:
        return dcc.send_file(zipfile_path,filename=project_name+".zip")
    finally:
        os.remove(zipfile_path)
        shutil.rmtree(os.path.join("tmp/",username))


# @app.server.route('/download-zip/<path:filename>')
# def download_zip(filename):
#     debug_print("in download_zip")
#     try:
#         file_path = '/tmp/downloads/' + filename
#         return flask.send_file(file_path, attachment_filename=filename, as_attachment=True)
#     finally:
#         os.remove(file_path)  # delete the file after sending it


@app.callback(
        Output({'type': 'file-item-checklist', 'index': ALL}, 'value'),
        Input('select-all-checklist','value'),
        State({'type': 'file-item-checklist', 'index': ALL}, 'options'),
        prevent_initial_call = True
)
def select_deselect_all_files(select_all,filename_options):
    #debug_print("in select_deselect_all_files")
    #debug_print("select_all:",select_all)
    #debug_print("filename_options",filename_options)
    if select_all != []:
        return [options for options in filename_options]
    else:
        return [[] for options in filename_options]


@app.callback(Output('upload-notify', 'children'),
              Output("upload-notify",'is_open'),
              Input('file-uploader', 'contents'),
              State('file-uploader', 'filename'),
              #State('session','data'),
              State('selected-project','data'),
              prevent_initial_call = True
)
def file_upload(list_of_contents, list_of_names,selected_project):
    try:  # Start a try block for error handling
        debug_print("Upload callback triggered")  # Print statement to check if function is triggered
        username = get_user_from_session()
        if username is None:
            return "Invalid user", True
        if not selected_project:
            return "Select a project first", True
        elif list_of_contents is not None:
            debug_print(list_of_names)
            children = []
            for content, name in zip(list_of_contents, list_of_names):
                if len(name) > 4 and (name[-4:] == ".jpg" or name[-4:] == ".png"):
                    data = content.split(',')[1]
                    filename_on_s3 = "images/"+username+"/"+selected_project+"/"+name
                    img_bytes = base64.b64decode(data)
                    s3_bucket.put_object(Key=filename_on_s3, Body=img_bytes)

                    # Convert bytes to a numpy array
                    nparr = np.frombuffer(img_bytes, np.uint8)

                    # Decode the numpy array as image
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    #EXECUTOR.submit(generate_sgbdi_file,img_np,username,selected_project,name)

                    children.append(html.Div('File "{}" uploaded successfully to S3.'.format(name)))
                elif len(name) > 6 and name[-6:] == ".sgbdi":
                    data = content.split(',')[1]
                    filename_on_s3 = "image_masks/"+username+"/"+selected_project+"/"+name
                    try:
                        s3_bucket.put_object(Key=filename_on_s3, Body=base64.b64decode(data))
                        children.append(html.Div('SegBuilder Archive File "{}" uploaded successfully to S3.'.format(name)))
                    except Exception as e: 
                        return f"Error uploading sgbdi file: {e}", True  # Return the error message
                else:
                    children.append(html.Div('File "{}" not uploaded - must be .jpg or .png'.format(name)))
            return children, True
        return no_update, no_update
    except Exception as e:  # Catch any exceptions
        return f"An error occurred: {e}", True  # Return the error message

# @app.callback(
#         #Output('session-data-display','children'),
#         Output('username-display','children'),
#         Input('session','data')
# )
# def show_session_data(session_data):
#     if session_data is not None:
#         session_id = session_data.get("session_id")
#         if session_id is not None:
#             user_data = session.get(session_id)
#             if user_data is not None:
#                 username = user_data.get("username")
#                 return "User: "+str(username)+" "
#             else:
#                 return "user_data is None"
#         else:
#             return "session_id is None"
#     else:
#         return "session_data is None"

"""
@app.callback(
    Output('username-display', 'children'),
    [Input('session', 'modified_timestamp')],  # we use this as dummy Input to ensure callback fires whenever the session changes
    #[State('session', 'data')]
)
def show_session_data(n):
    username = session.get('username')
    if username is not None:
        return "User: " + str(username) + " "
    else:
        return "No username found in session."
"""

@app.callback(
    #Output('session', 'data'),  # Output the user's data to the 'session' store
    Output('username-display','children'),
    Output('login-content','style'),
    Output('main-content','style'),
    Output("invalid-password-message",'style'),
    #Output('url','pathname'),
    #Output("project-select-dropdown",'options'),
    Output("project-cards","children"),
    #Input('url', 'pathname'),
    Input('login-button', 'n_clicks'),
    Input('new-project-has-been-created','data'),
    Input('logout-button','n_clicks'),
    State('login-username', 'value'),
    State('login-password', 'value'),
    #State('session','data'),
    prevent_initial_call = True
)
def manage_session(n_clicks, new_proj, logout_n, username, password):
    debug_print("SBDEBUG: In manage session callback")
    if callback_context.triggered_id == "login-button":
        debug_print("SBDEBUG: login button triggered")

        if n_clicks and n_clicks > 0:
            user = load_user(username)
            if user and user.check_password(password):

                debug_print("SBDEBUG SESSION: setting session['username'] to ",user.id)
                session['username'] = user.id
                debug_print("SBDEBUG SESSION: now let's see what's in session['username'] to ",session['username'])

                # #generate a unique session id and store it in the session
                # session_id = uuid.uuid4().hex
                # session["session_id"] = session_id

                # #put the session_id in the DynamoDB sessions table
                # sessions_table = dynamodb.Table('sessions')
                # sessions_table.put_item(
                #    Item={
                #         'session_id': session_id,
                #         'username': user.id,
                #         'last_activity': datetime.datetime.now().isoformat(), 
                #     }
                # )
                # session['username'] = user.id
                debug_print("SBDEBUG: about to populate project cards")
                project_cards = populate_project_cards(user.id)
                debug_print("SBDEBUG: project cards created, about to return them.")
                return user.id, {'display':"none"}, {"display":"block"}, {'display':"none"}, project_cards
            else:
                debug_print("invalid username/password")
                return "User: None ", no_update, no_update, {'display':"block"}, no_update
        else:
            raise PreventUpdate
    elif callback_context.triggered_id == "new-project-has-been-created" and new_proj:
        username = get_user_from_session()
        project_cards = populate_project_cards(username)
        debug_print("finished updating new project cards")
        return no_update, no_update, no_update, no_update, project_cards
    elif callback_context.triggered_id == "logout-button":
        if logout_n and logout_n > 0:
            debug_print("got to logout callback")
            session_id = session.get('session_id')

            #!!TODO: add error handling in case we lose connection to DynamoDB
            # Remove the session data from DynamoDB
            if session_id:
                sessions_table = dynamodb.Table('sessions')
                sessions_table.delete_item(Key={'session_id': session_id})
            session.clear()
            # Clear the session data
            return "User: None ", {"display":"block"}, {'display':"none"}, {'display':"none"}, []
    else:
        debug_print("uncaught trigger:",callback_context.triggered_id)
        raise PreventUpdate




@app.callback(
        Output("save-notify",'children'),
        Output("save-notify",'is_open'),
        Input('save-button','n_clicks'),
        State("new-mask-store","data"),
        State({'type': 'label-dropdown', 'index': ALL}, 'value'),
        State({'type': 'new-label-dropdown', 'index': ALL}, 'value'),
        State('selected-project','data'),
        State('selected-image','data'),
        State("mask-image",'src'),
        #State("session","data"),
        prevent_initial_call = True
)
def perform_save(n_clicks,new_masks,old_mask_labels,new_mask_labels,selected_project,selected_image,segmented_image):
    if n_clicks:
        username = get_user_from_session()
        image_obj = SB_project_image(username,selected_project,selected_image)
        image_obj.update_archive(old_mask_labels,new_masks,new_mask_labels)
        image_obj.save_segmented_image(segmented_image)
        message = str(selected_image)+" saved "+str(datetime.datetime.now())
        return message, True
    return "not saved recently", False


@app.callback(
        Output('create-project-modal','is_open'),
        Input('new-project-card','n_clicks'),
        Input('tabs','active_tab'),
        prevent_initial_call = True
)
def open_new_project_modal(n_clicks,active_tab):
    if callback_context.triggered_id == 'new-project-card':
        if n_clicks:
            return True
    elif callback_context.triggered_id == 'tabs':
        return False
    return no_update

def generate_label_cards(classes_table,username,project_name):
    label_records = classes_table.get_item(Key={'username-projectname':username+"-"+project_name})["Item"]["classes"]
    label_cards = []
    for r in label_records:
        #debug_print("record label",r)
        label_card = dbc.Card([
            dbc.CardBody(style={"backgroundColor":"rgb({},{},{})".format(*r["color"])}),
            dbc.CardFooter(r["name"],style={"textAlign":"center"})
        ],style={"width":"8rem","height":"8rem","float":"left","marginLeft":"1rem"})
        label_cards.append(label_card)
    return label_cards

@app.callback(
        Output("label-color-map-display","children"),
        Output("project-name-display-on-classes","children"),
        Output("project-name-display-on-files","children"),
        Input("selected-project","data"),
        Input("new-class-label-button","n_clicks"),
        Input("label-color-scheme-upload","contents"),
        #State("session","data"),
        State("class-label-input","value"),
        State("class-colorpicker","value"),
        prevent_initial_call = True
)
def populate_classes_tab(project_name,n_clicks,json_file_contents,new_label,new_color):
    debug_print("POPULATECLASSES: callback_context.triggered_id",callback_context.triggered_id)
    username = get_user_from_session()
    if callback_context.triggered_id == "label-color-scheme-upload":
        if json is not None:
            content_type, content_string = json_file_contents.split(',')
            decoded = base64.b64decode(content_string)
            data = json.load(io.StringIO(decoded.decode('utf-8')))
            classes_table = dynamodb.Table("project-classes")
            classes_table.put_item(Item={
                "username-projectname":username+"-"+project_name,
                "classes":data
            })
            label_cards = generate_label_cards(classes_table,username,project_name)
            return label_cards, no_update, no_update
    elif callback_context.triggered_id == "selected-project":
        if project_name:
            username = get_user_from_session()
            classes_table = dynamodb.Table("project-classes")
            label_cards = generate_label_cards(classes_table,username,project_name)
            return label_cards, project_name, project_name
        
    elif callback_context.triggered_id == "new-class-label-button":
        if n_clicks:
            
            classes_table = dynamodb.Table("project-classes")
            label_records = classes_table.get_item(Key={'username-projectname':username+"-"+project_name})["Item"]["classes"]
            debug_print(label_records)
            debug_print(new_label,new_color)
            label_records.append({"name":new_label,"color":hex_to_rgb(new_color)})
            classes_table.put_item(Item={
                "username-projectname":username+"-"+project_name,
                "classes":label_records
            })
            label_cards = generate_label_cards(classes_table,username,project_name)
            return label_cards, no_update, no_update

    return no_update, no_update, no_update

@app.callback(
        Output('file-list-group','children'),
        Output('selected-project','data'),
        Output("selected-image","data"),
        Output("tabs","active_tab"),
        Output("filename-display","children"),
        Output("create-new-project-name-message","style"),
        Output('new-project-has-been-created','data'),
        
        Input({'type': 'file-item', 'index': ALL}, 'n_clicks'),
        Input({'type': 'project-card', 'index': ALL}, 'n_clicks'),
        Input("create-project-button","n_clicks"),
        Input("upload-notify","children"),
        Input("refresh-button","n_clicks"),


        #State('session','data'),
        State("create-project-name-input","value"),
        State('selected-project','data'),
        prevent_initial_call = True
)
def tab_navigation(files_n_clicks,project_cards_n_clicks,create_project_n_clicks,upload_notification,refresh_button_clicks,new_project_name,curr_selected_project):
    debug_print("SBDEBUG: tab_navigation callback_context.triggered_id",callback_context.triggered_id)
    debug_print(" SBDEBUG: create_project_n_clicks",create_project_n_clicks)
    debug_print(" SBDEBUG: project_cards_n_clicks",project_cards_n_clicks)
    username = get_user_from_session()
    debug_print(" SBDEBUG: got username from session ",username)
    if username is None or not callback_context.triggered: # or selected_project is None:
        debug_print(" SBDEBUG: username was none, we're preventing update")
        raise PreventUpdate
    elif callback_context.triggered_id == "create-project-button" and create_project_n_clicks:
        #!!TODO: check if project name already exists
        if new_project_name == "" or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$',new_project_name):
            return no_update, no_update, no_update, no_update, no_update, {"display":"block"}, no_update
        else:
            curr_projects = []
            projects_table = dynamodb.Table("projects")
            curr_projects_response = projects_table.get_item(Key={"username":username})
            if "Item" in curr_projects_response:
                curr_projects = curr_projects_response["Item"]["projects"]
            debug_print("curr_projects",curr_projects)
            curr_projects.append(new_project_name)
            projects_table.put_item(Item={"username":username,"projects":curr_projects})


            project_init_classes = [{"name": "unlabeled","color": [0,0,0]}]
            classes_table = dynamodb.Table("project-classes")
            classes_table.put_item(Item={"username-projectname":(username+"-"+new_project_name),"classes":project_init_classes})
            return populate_files(username,new_project_name), new_project_name, None, "classes_tab", no_update, {"display":"none"}, True
    elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'project-card' and not all(n is None for n in project_cards_n_clicks):
        project_name = callback_context.triggered_id["index"]
        debug_print("SBDEBUG: tab_navigation callback, project selected:"+str(project_name))
        return populate_files(username,project_name), project_name, None, "files_tab", no_update, no_update, no_update
    elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'file-item':
        filename = callback_context.triggered_id["index"]
        debug_print("filename",filename)
        return no_update, no_update, filename, "annotate_tab", filename, no_update, no_update
    elif callback_context.triggered_id == "upload-notify":
        return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update 
    elif callback_context.triggered_id == "refresh-button" and refresh_button_clicks:
        return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update
    elif callback_context.triggered[0]["value"] is None: #!! Do I still need this?
        raise PreventUpdate
    else:
        debug_print("uncaught trigger in tab_navigation")
        raise PreventUpdate

        



@app.callback(
    Output({'type': 'label-dropdown', 'index': MATCH}, 'value'),
    Output({'type': 'mask-card', 'index': MATCH}, 'style'),
    Input({'type': 'delete-button', 'index': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_mask_card(n_clicks):
    if not n_clicks is None:
        return "DELETE", {'display':'none'}
    return no_update, no_update

@app.callback(
    Output({'type': 'new-label-dropdown', 'index': MATCH}, 'value'),
    Output({'type': 'new-mask-card', 'index': MATCH}, 'style'),
    Input({'type': 'new-delete-button', 'index': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_new_mask_card(n_clicks):
    if not n_clicks is None:
        #debug_print("deleting mask card",callback_context.triggered_id)
        return "DELETE", {'display':'none'}
    return no_update, no_update

@app.callback(
        Output({'type': 'delete-button', 'index': ALL}, 'n_clicks'),
        Output("mask-card-move-to-front","data"),
        Output("mask-move-to-front","data"),
        Input({'type': 'front-button', 'index': ALL}, 'n_clicks'),
        State('selected-project','data'),
        State('selected-image','data'),
        State({'type': 'label-dropdown', 'index': ALL}, 'value'),
        State('new-mask-display','children'),
        #State("session","data"),
        prevent_initial_call=True
)
def front_button_handle(n_clicks,selected_project,selected_image_name,curr_labels,current_new_masks_display):
    debug_print("front_button_handle triggered with",callback_context.triggered_id)
    if not all(n is None for n in n_clicks):
        #debug_print("something wasn't None")
        username = get_user_from_session()
        mask_num = callback_context.triggered_id["index"]
        image_obj = SB_project_image(username,selected_project,selected_image_name)
        image = image_obj.load_image()
        mask_to_move = image_obj.load_masks()[mask_num]
        label_options = get_label_options(username,selected_project)
        new_card = create_mask_cards(image,[mask_to_move],[curr_labels[mask_num]],label_options=label_options,new_masks=True,index_offset=len(current_new_masks_display))
        delete_clicks = [None]*len(n_clicks)
        delete_clicks[mask_num] = 1
        return delete_clicks, new_card, mask_to_move
    return [no_update]*len(n_clicks), no_update, no_update


@app.callback(
    Output('mask-display', 'children'),
    Output('graph-draw','figure'),
    Output('new-mask-display','children'),
    Output('new-mask-store','data'),
    Output("mask-composite-image","src"),
    Output("mask-image","src"),
    #Output({'type': 'new-delete-button', 'index': ALL}, 'n_clicks'),

    
    Input('selected-image','data'),
    Input('generate-manual-mask-button','n_clicks'),
    Input("generate-composite-image-button","n_clicks"),
    Input("mask-card-move-to-front","data"),
    Input({'type': 'new-front-button', 'index': ALL}, 'n_clicks'),
    Input("save-notify",'children'),
    


    State('selected-project','data'),
    State('new-mask-store','data'),
    State('new-mask-display','children'),
    State('closed-paths-store','data'),
    State({'type': 'label-dropdown', 'index': ALL}, 'value'),
    State({'type': 'new-label-dropdown', 'index': ALL}, 'value'),
    State("mask-move-to-front","data"),
    #State("session","data"),
    prevent_initial_call=True
)
def update_annotation_page(selected_image_name,generate_manual_n_clicks,gen_composite_n_clicks,new_front_mask_card,nfb_n_clicks,save_notify,selected_project,current_new_masks,current_new_display_cards,closed_paths,labels,new_labels,new_front_mask):
    username = get_user_from_session()
    no_update_ALL = [no_update]*len(nfb_n_clicks)
    debug_print("update_annotation_page selected_image_name",selected_image_name)

    #load everything if they selected a new image or saved
    if callback_context.triggered_id == "selected-image" or callback_context.triggered_id == "save-notify":
        if not selected_image_name:
            raise PreventUpdate
            #return None, None, None, None, None, None #, no_update_ALL
        else:
            pen_color = "white"
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            if image_obj.has_masks():
                
                image = image_obj.load_image() 
                masks = image_obj.load_masks()
                labels = image_obj.load_labels()
                label_options = get_label_options(username,selected_project)
                display_cards = create_mask_cards(image,masks,labels,label_options=label_options)
                fig_image = px.imshow(image)
                fig_image.update_layout(dragmode="drawclosedpath",
                                        width=CANVAS_WIDTH,
                                        height=1000,
                                        #margin=dict(t=0, b=5, l=5, r=5),  # Set the top margin to 0
                                        #title=dict(text='', pad=dict(t=0, b=0, l=0, r=0)),
                                        newshape=dict(line=dict(color=pen_color)))
                #debug_print("fig_image",fig_image)
                segmented_image = ""
                composite_image = ""
                if image_obj.has_segmented_image():
                    composite_image, segmented_image = make_composite_image(image,image_obj.load_segmented_image())
                return display_cards, fig_image, [], None, composite_image, segmented_image #, no_update_ALL
            
            else:
                
                debug_print("loading",selected_image_name,"without pre-computed masks")
                image = image_obj.load_image() 
                fig_image = px.imshow(image)
                fig_image.update_layout(dragmode="drawclosedpath",
                                            #width=CANVAS_WIDTH,
                                            height=1000,
                                            #margin=dict(t=0, b=5, l=5, r=5),  # Set the top margin to 0
                                            #title=dict(text='', pad=dict(t=0, b=0, l=0, r=0)),
                                            newshape=dict(line=dict(color=pen_color)))
                segmented_image = ""
                composite_image = ""
                if image_obj.has_segmented_image():
                    composite_image, segmented_image = make_composite_image(image,image_obj.load_segmented_image())

                return [], fig_image, [], None, composite_image, segmented_image #, no_update_ALL
    
    elif callback_context.triggered_id == "generate-manual-mask-button":
        image_obj = SB_project_image(username,selected_project,selected_image_name)
        image = image_obj.load_image()
        debug_print("closed_paths",closed_paths)
        new_mask = create_mask_from_paths(closed_paths,image.shape)
        masks_meta = add_meta_info_to_masks([new_mask])
        label_options = get_label_options(username,selected_project)
        #debug_print("label_options",label_options)
        new_row = create_mask_cards(image,masks_meta,[label_options[0]],label_options=label_options,new_masks=True,index_offset=len(current_new_display_cards))
        new_display_cards = new_row
        if current_new_display_cards:
            new_display_cards += current_new_display_cards
        new_masks_store = masks_meta
        if current_new_masks:
            new_masks_store += current_new_masks
        return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
    

    elif callback_context.triggered_id == "generate-composite-image-button":
        image_obj = SB_project_image(username,selected_project,selected_image_name)
        image = image_obj.load_image()
        masks = image_obj.load_masks()
        debug_print("masks loaded")
        mask_image = np.zeros_like(image)
        label_colors_dict = get_label_colors_dict(username,selected_project)
        

        for i in range(len(masks)-1,-1,-1):
            #debug_print("i",i)
            curr_label = labels[i]
            #debug_print("curr_label",curr_label)
            if curr_label != "DELETE":
                curr_mask = np.array(masks[i]["segmentation"])
                
                color = label_colors_dict[curr_label]
                colored_mask = np.zeros_like(image)
                colored_mask[curr_mask > 0] = color
                mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

        if current_new_masks:
            for i in range(len(current_new_masks)-1,-1,-1):
                curr_label = new_labels[i]
                if curr_label != "DELETE":
                    curr_mask = np.array(current_new_masks[i]["segmentation"])
                    color = label_colors_dict[curr_label]
                    colored_mask = np.zeros_like(image)
                    colored_mask[curr_mask > 0] = color
                    mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

        composite_image, segmented_image = make_composite_image(image,mask_image)


        return no_update, no_update, no_update, no_update, composite_image, segmented_image #, no_update_ALL
    
    elif callback_context.triggered_id == "mask-card-move-to-front":
        new_display_cards = new_front_mask_card
        if current_new_display_cards:
            new_display_cards += current_new_display_cards
        new_masks_store = [new_front_mask]
        if current_new_masks:
            new_masks_store += current_new_masks
        return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
    

    elif 'type' in callback_context.triggered_id and callback_context.triggered_id["type"] == "new-front-button" and not(all(n is None for n in nfb_n_clicks)):
        image_obj = SB_project_image(username,selected_project,selected_image_name)
        image = image_obj.load_image()
        mask_num = callback_context.triggered_id["index"]
        new_front_mask = current_new_masks[mask_num]
        current_new_display_cards.pop(mask_num)
        label_options = get_label_options(username,selected_project)
        new_display_cards = create_mask_cards(image,[new_front_mask],[new_labels[mask_num]],label_options=label_options,new_masks=True,index_offset=len(current_new_display_cards))
        if current_new_display_cards:
            new_display_cards += current_new_display_cards
        new_masks_store = [new_front_mask]
        if current_new_masks:
            new_masks_store += current_new_masks
        new_delete_clicks = [None]*len(nfb_n_clicks)
        new_delete_clicks[mask_num] = 1
        return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, new_delete_clicks

    debug_print("uncaught context:",callback_context.triggered_id)
    return no_update, no_update, no_update, no_update, no_update, no_update #, no_update_ALL

@app.callback(
    #Output('canvas-message', 'children'),
    Output('drawings-store','data'),
    Output('closed-paths-store','data'),
    Input('graph-draw', 'relayoutData'),
    #State('image-store','data'),
    #State('canvas','height'),
    #State('canvas','width'),
    prevent_initial_call=True
)
def update_click_coordinates(shape_data):
    #image = np.array(image)
    #image = image.astype(np.uint8)
    #debug_print(type(shape_data))
    debug_print("shape data",shape_data)
    #image_width = image.shape[0]
    #image_height = image.shape[1]

    #image_scale_factor = image_width/CANVAS_WIDTH
    
    #debug_print("image:",image.shape)
    #debug_print("canvas:",canvas_height,", ",canvas_width)
    coords = []
    closed_paths = []
    if "shapes" in shape_data:
        for shape in shape_data["shapes"]:
            if shape["type"] == "circle":
                include = 1
                if shape["line"]["color"] == "red":
                    include = 0 
                x = (shape["x0"]+shape["x1"])/2
                y = (shape["y0"]+shape["y1"])/2
                coords.append([include,x,y])
            if shape["type"] == "path":
                #closed path
                if shape["path"][-1] == "Z":
                    indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                    closed_path_indices = [(float(p[0]),float(p[1])) for p in indices_str]
                    closed_paths.append(closed_path_indices)
                else:
                    include = 1
                    if shape["line"]["color"] == "red":
                        include = 0 
                    indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                    indices_float = [[include,float(p[0]),float(p[1])] for p in indices_str]
                    #debug_print(indices_float)
                    coords += indices_float
    for k in shape_data:
        if 'shapes[' in k and '].path' in k and shape_data[k][-1] == "Z":
            indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape_data[k].split("L")]
            closed_path_indices = [(float(p[0]),float(p[1])) for p in indices_str]
            closed_paths.append(closed_path_indices)
    if len(coords) == 0:
        coords = no_update
    if len(closed_paths) == 0:
        closed_paths = no_update
    return coords, closed_paths


# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    application.run(host="0.0.0.0")