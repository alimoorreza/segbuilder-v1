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
        """
        Callback to handle downloading the label color JSON scheme file for the current project.

        Outputs:
        - label-color-scheme-download: Data for the downloadable file containing the label color scheme.

        Inputs:
        - download-label-color-scheme-button (n): Number of clicks on the 'Download Label Color Scheme' button.

        States:
        - selected-project (project_name): The name of the currently selected project.

        """
        username = get_user_from_session()
        # check if the button was actually clicked
        if n:
            db_result = get_db_item(table_name="project-classes",key_name='username-projectname',key_value=(username+"-"+project_name),default_return={"classes":[]})
            label_records = db_result["classes"]
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
        """
        Callback to handle the initiation of a zip file download for the current project's selected
         files that are stored on the server.

        Outputs:
        - download-zipfile: Data for the downloadable zip file containing the project's files.

        Inputs:
        - download-button (n): Number of clicks on the 'Download' button.

        States:
        - file-item-checklist (filename_checklist_values): Values indicating which files are selected for download.
        - file-item (filenames): The names of the files available for selection.
        - selected-project (project_name): The name of the current project.
        """
        logging.debug("DOWNLOADDEBUG: in initiate_download, nclicks: %s",n)
        logging.debug("DOWNLOADDEBUG: filename_checklist_values: %s",filename_checklist_values)
        logging.debug("DOWNLOADDEBUG: filenames: %s",filenames)
        username = get_user_from_session()
        if not username:
            raise PreventUpdate
        
        # Initialize a list to store the files to be downloaded
        download_files = []
        # Iterate through the checklist values to determine which files are selected
        for idx in range(len(filename_checklist_values)):
            if filename_checklist_values[idx] != []:
                download_files.append(filenames[idx])

        logging.debug("DOWNLOADDEBUG: download_files %s",download_files)

        # Create a project instance for the user and project name
        project = SB_project(username,project_name)

        # Generate a unique filename for the temporary zip file on the server
        unique_filename = str(uuid.uuid4()) + '.zip'

        # Prepare the zip file for download
        zipfile_path = project.prepare_download(download_files,unique_filename)
        logging.debug("DOWNLOADDEBUG: zip created")
        try:
            # send the file as a download
            return dcc.send_file(zipfile_path,filename=project_name+".zip")
        finally:
            # Clean up the temporary zip file and directory
            os.remove(zipfile_path)
            shutil.rmtree(os.path.join("tmp/",username))


    @app.callback(Output('upload-notify', 'children'),
                Output("upload-notify",'is_open'),
                Input('file-uploader', 'contents'),
                State('file-uploader', 'filename'),
                State('selected-project','data'),
                prevent_initial_call = True
    )
    def file_upload(list_of_contents, list_of_names,selected_project):
        """
        Callback to handle the file upload process for files (image and sgbdi) 
        for the current project.

        Outputs:
        - upload-notify (children): Notification messages regarding the upload status.
        - upload-notify (is_open): Boolean indicating if the notification should be shown.

        Inputs:
        - file-uploader (list_of_contents): List of contents of the uploaded files.

        States:
        - file-uploader (list_of_names): List of names of the uploaded files.
        - selected-project (selected_project): The name of the current project.
        """
        try:  # Start a try block for error handling
            logging.debug("Upload callback triggered")  # Print statement to check if function is triggered
            username = get_user_from_session()

            if username is None:
                return "Invalid user", True
            
            if not selected_project:
                return "Select a project first", True
            
            # If files are actually uploaded
            elif list_of_contents is not None:
                logging.debug("%s",str(list_of_names))

                # initialize notification messages
                children = []

                # iterate over uploaded files
                for content, name in zip(list_of_contents, list_of_names):

                    # check if it's an image file (jpg or png)
                    if len(name) > 4 and (name[-4:] == ".jpg" or name[-4:] == ".png"):
                        data = content.split(',')[1]
                        filename_on_server = "images/"+username+"/"+selected_project+"/"+name
                        img_bytes = base64.b64decode(data)

                        write_file(filename_on_server,img_bytes)

                        # Convert bytes to a numpy array
                        nparr = np.frombuffer(img_bytes, np.uint8)

                        # Decode the numpy array as image
                        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        # add success message to notifications
                        children.append(html.Div('File "{}" uploaded successfully.'.format(name)))

                    # check if it is a SegBuilder archive (with masks and labels)
                    elif len(name) > 6 and name[-6:] == ".sgbdi":
                        data = content.split(',')[1]
                        filename_on_server = "image_masks/"+username+"/"+selected_project+"/"+name
                        try:
                            write_file(filename_on_server,base64.b64decode(data))
                            # add success message to notifications
                            children.append(html.Div('SegBuilder Archive File "{}" uploaded successfully.'.format(name)))
                        except Exception as e: 
                            return f"Error uploading sgbdi file: {e}", True  # Return the error message
                    # other file types are not supported
                    else:
                        children.append(html.Div('File "{}" not uploaded - must be .jpg or .png image or a .sgbdi SegBuilder archive'.format(name)))
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
            prevent_initial_call = True
    )
    def perform_save(n_clicks,new_masks,old_mask_labels,new_mask_labels,selected_project,selected_image,segmented_image):
        """
        Callback to handle saving the current state of image segmentation for the selected project and image.

        Outputs:
        - save-notify (children): Notification message indicating the save status.
        - save-notify (is_open): Boolean indicating if the notification should be shown.

        Inputs:
        - save-button (n_clicks): Number of clicks on the 'Save' button.

        States:
        - new-mask-store (new_masks): Data stored in the browser for the new masks created during annotation.
        - label-dropdown (old_mask_labels): The existing mask labels.
        - new-label-dropdown (new_mask_labels): The new mask labels.
        - selected-project (selected_project): The name of the currently selected project.
        - selected-image (selected_image): The name of the currently selected image.
        - mask-image (segmented_image): img tag src data for the composite mask image
        """
        # check if the save button was actually clicked
        if n_clicks:
            username = get_user_from_session()
            image_obj = SB_project_image(username,selected_project,selected_image)
            # save new (in browser) and old masks to storage
            image_obj.update_archive(old_mask_labels,new_masks,new_mask_labels)
            # save the composite mask image to storage 
            image_obj.save_segmented_image(segmented_image)
            message = str(selected_image)+" saved "+str(datetime.datetime.now())
            return message, True
        return "not saved recently", False
