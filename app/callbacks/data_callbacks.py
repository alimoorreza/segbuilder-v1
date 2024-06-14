from dash.dependencies import Input, Output, State, ALL
import simplejson as json
import datetime
from dash import html, dcc, no_update
from dash.exceptions import PreventUpdate
import shutil
import cv2
import base64
import uuid
import numpy as np
import os
import logging

from ..data import get_user_from_session
from ..resources import get_db_item #get_dynamodb_resource
from ..project_models import SB_project_image, SB_project
from ..resources import write_file

def register_data_callbacks(app):

    @app.callback(
        Output('label-color-scheme-download',"data"),
        Input("download-label-color-scheme-button","n_clicks"),
        State("selected-project","data"),
        prevent_initial_callback=True
    )
    def download_label_color_scheme_file(n,project_name):
        username = get_user_from_session()
        if n:
            db_result = get_db_item(table_name="project-classes",key_name='username-projectname',key_value=(username+"-"+project_name),default_return={"classes":[]})
            label_records = db_result["classes"]
            #dynamodb = get_dynamodb_resource()
            #classes_table = dynamodb.Table("project-classes")
            #label_records = classes_table.get_item(Key={'username-projectname':username+"-"+project_name})["Item"]["classes"]
            return dict(content=json.dumps(label_records),filename=project_name+".json")
        return no_update



    @app.callback(
        Output('download-zipfile','data'),
        Input("download-button","n_clicks"),
        State({'type': 'file-item-checklist', 'index': ALL}, 'value'),
        State({'type': 'file-item', 'index': ALL}, 'children'),
        State('selected-project','data'),
        prevent_initial_call = True
    )
    def initiate_download(n,filename_checklist_values,filenames,project_name):
        logging.debug("DOWNLOADDEBUG: in initiate_download, nclicks: %s",n)
        logging.debug("DOWNLOADDEBUG: filename_checklist_values: %s",filename_checklist_values)
        logging.debug("DOWNLOADDEBUG: filenames: %s",filenames)
        username = get_user_from_session()
        if not username:
            raise PreventUpdate
        download_files = []
        for idx in range(len(filename_checklist_values)):
            if filename_checklist_values[idx] != []:
                download_files.append(filenames[idx])
        #download_files = [filename for filename in filenames if file != []]
        logging.debug("DOWNLOADDEBUG: download_files %s",download_files)
        project = SB_project(username,project_name)
        unique_filename = str(uuid.uuid4()) + '.zip'
        zipfile_path = project.prepare_download(download_files,unique_filename)
        logging.debug("DOWNLOADDEBUG: zip created")
        try:
            return dcc.send_file(zipfile_path,filename=project_name+".zip")
        finally:
            os.remove(zipfile_path)
            shutil.rmtree(os.path.join("tmp/",username))


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
            logging.debug("Upload callback triggered")  # Print statement to check if function is triggered
            username = get_user_from_session()
            if username is None:
                return "Invalid user", True
            if not selected_project:
                return "Select a project first", True
            elif list_of_contents is not None:
                logging.debug("%s",str(list_of_names))
                children = []
                for content, name in zip(list_of_contents, list_of_names):
                    if len(name) > 4 and (name[-4:] == ".jpg" or name[-4:] == ".png"):
                        data = content.split(',')[1]
                        filename_on_server = "images/"+username+"/"+selected_project+"/"+name
                        img_bytes = base64.b64decode(data)

                        write_file(filename_on_server,img_bytes)

                        # Convert bytes to a numpy array
                        nparr = np.frombuffer(img_bytes, np.uint8)

                        # Decode the numpy array as image
                        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        #EXECUTOR.submit(generate_sgbdi_file,img_np,username,selected_project,name)

                        children.append(html.Div('File "{}" uploaded successfully.'.format(name)))
                    elif len(name) > 6 and name[-6:] == ".sgbdi":
                        data = content.split(',')[1]
                        filename_on_server = "image_masks/"+username+"/"+selected_project+"/"+name
                        try:
                            write_file(filename_on_server,base64.b64decode(data))
                            #s3_bucket.put_object(Key=filename_on_s3, Body=base64.b64decode(data))
                            children.append(html.Div('SegBuilder Archive File "{}" uploaded successfully to S3.'.format(name)))
                        except Exception as e: 
                            return f"Error uploading sgbdi file: {e}", True  # Return the error message
                    else:
                        children.append(html.Div('File "{}" not uploaded - must be .jpg or .png'.format(name)))
                return children, True
            return no_update, no_update
        except Exception as e:  # Catch any exceptions
            return f"An error occurred: {e}", True  # Return the error message


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
