
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash import Dash, html, dcc, ctx, no_update, callback_context
import dash_bootstrap_components as dbc
import base64
import simplejson as json
import io
from dash.exceptions import PreventUpdate
import re
import plotly.express as px
import numpy as np
import logging
import cv2
import plotly.graph_objs as go

from ..data import get_user_from_session
#from ..resources import get_dynamodb_resource
from ..project_models import SB_project_image
from ..utils import populate_files, create_mask_cards, hex_to_rgb, make_composite_image, create_mask_from_paths, add_meta_info_to_masks, contours_from_mask, plotly_shapes_from_contours, get_label_options, get_label_colors_dict,  generate_label_cards
from ..resources import get_db_item, put_db_item

CANVAS_WIDTH = 600

def register_ui_callbacks(app):

    @app.callback(
            Output({'type': 'file-item-checklist', 'index': ALL}, 'value'),
            Input('select-all-checklist','value'),
            State({'type': 'file-item-checklist', 'index': ALL}, 'options'),
            prevent_initial_call = True
    )
    def select_deselect_all_files(select_all,filename_options):
        """
        Callback to handle select-all (or to deselect-all) of the files check boxes in a project

        Outputs:
        - file-item-checklist: a list of check box values for each file.

        Inputs:
        - select-all-checklist (select_all): It's a list of size one representing the value of the "select all" check list.

        States:
        - file-item-checklist (filename_options): List of labels associated with the check boxes for each image - these are
            dummies with the "" value - we're showing the label separately
        """

        if select_all != []:
            # select the dummy option "" for each of the checklist items
            return [options for options in filename_options]
        else:
            # unselect each check list
            return [[] for options in filename_options]



    @app.callback(
            Output('create-project-modal','is_open'),
            Input('new-project-card','n_clicks'),
            Input('tabs','active_tab'),
            prevent_initial_call = True
    )
    def open_new_project_modal(n_clicks,active_tab):
        """
        Callback to handle showing the "create project" dialog (which is a modal component)

        Outputs:
        - create-project-modal: value of the is_open property of the modal

        Inputs:
        - new-project-card (n_clicks): Number of times the new project card (actually, its html div container) has been clicked
        - tabs (active_tab): the active tab - so we can close the modal if the user clicks another tab
        """
        if callback_context.triggered_id == 'new-project-card':
            if n_clicks:
                return True
        elif callback_context.triggered_id == 'tabs':
            return False
        return no_update



    @app.callback(
            Output("label-color-map-display","children"),
            Output("project-name-display-on-classes","children"),
            Output("project-name-display-on-files","children"),
            Input("selected-project","data"),
            Input("new-class-label-button","n_clicks"),
            Input("label-color-scheme-upload","contents"),
            State("class-label-input","value"),
            State("class-colorpicker","value"),
            prevent_initial_call = True
    )
    def populate_classes_tab(project_name,n_clicks,json_file_contents,new_label,new_color):
        """
        Callback to populate the classes tab with colors/labels.
        It also displasy the project name on both the classes and files tabs.

        Outputs:
        - label-color-map-display: Updated display of label color mapping cards.
        - project-name-display-on-classes: Display of the project name on the classes tab.
        - project-name-display-on-files: Display of the project name on the files tab.

        Inputs:
        - selected-project (project_name): The name of the selected project.
        - new-class-label-button (n_clicks): Number of clicks on the 'New Class Label' button.
        - label-color-scheme-upload (json_file_contents): Contents of the uploaded JSON file for label color schemes.

        States:
        - class-label-input (new_label): Value user has typed into the new class label input field.
        - class-colorpicker (new_color): Value of the color the user has picked for the new class label.
        """
        logging.debug("POPULATECLASSES: callback_context.triggered_id %s",callback_context.triggered_id)
        username = get_user_from_session()

        # handle when the user has uploaded JSON file with the label-color scheme
        if callback_context.triggered_id == "label-color-scheme-upload":
            if json is not None:
                content_type, content_string = json_file_contents.split(',')
                decoded = base64.b64decode(content_string)
                data = json.load(io.StringIO(decoded.decode('utf-8')))

                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),item_name="classes",item_value=data)

                label_cards = generate_label_cards(username,project_name)
                return label_cards, no_update, no_update
            
        # handle when the user has selected a new project
        elif callback_context.triggered_id == "selected-project":
            if project_name:
                username = get_user_from_session()
                label_cards = generate_label_cards(username,project_name)
                return label_cards, project_name, project_name
            
        # handle when the user creates a new class (label and color) using the UI
        elif callback_context.triggered_id == "new-class-label-button":
            if n_clicks:

                # get the current label-color scheme from the database
                db_label_records = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),default_return=[])
                label_records = db_label_records["classes"]

                # add the new label-color pair onto the list
                label_records.append({"name":new_label,"color":hex_to_rgb(new_color)})

                # put the updated list back in the database
                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),item_name="classes",item_value=label_records)

                label_cards = generate_label_cards(username,project_name)
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

            State("create-project-name-input","value"),
            State('selected-project','data'),
            prevent_initial_call = True
    )
    def tab_navigation(files_n_clicks,project_cards_n_clicks,create_project_n_clicks,upload_notification,refresh_button_clicks,new_project_name,curr_selected_project):
        """
        Callback to handle switching between tabs or doing something else (like creating a new project) that switches to
        a new tab by default.

        Outputs:
        - file-list-group: the component that lists all of the files in the project
        - selected-project: the name of the selected project (browser store)
        - selected-image: the name of the image file selected within the current project (browser store)
        - tabs: the value of the currently selected tab
        - filename-display: the label/header for the filename on the annotate tab
        - create-new-project-name-message: visibility of the illegal project name message
        - new-project-has-been-created: browser store indicating a new project has been created - to trigger the next callback in project creation
            TODO: should this be an int instead of a boolean? Need to test what happens if multiple projects created in one session

        Inputs:
        - file-item (files_n_clicks) - a list the number of clicks over each file (one of these should increase when a new file is chosen)
        - project-card (project_cards_n_clicks) - a list of the number of clicks over each project (one of these should increase when a new project is chosen)
        - create-project-button (create_project_n_clicks) - number of clicks on the new project button
        - upload-notify (upload_notification) - indicates whether we have finished displaying that a new image file has completed uploaded
        - refresh-button (refresh_button_clicks) - number of clicks on the files tab refresh button

        States:
        - create-project-name-input (new_project_name) - the name the user has types into the new project name box
        - selected-project (curr_selected_project) - the currently selected project    
        """
        logging.debug("SBDEBUG: tab_navigation callback_context.triggered_id %s",callback_context.triggered_id)
        logging.debug(" SBDEBUG: create_project_n_clicks %s",create_project_n_clicks)
        logging.debug(" SBDEBUG: project_cards_n_clicks %s",project_cards_n_clicks)
        username = get_user_from_session()
        logging.debug(" SBDEBUG: got username from session %s",username)

        # if the user isn't logged in don't populate any info
        if username is None or not callback_context.triggered: # or selected_project is None:
            logging.debug(" SBDEBUG: username was none, we're preventing update")
            raise PreventUpdate
        
        # handle if the user creates a new project - switch to the classes tab
        elif callback_context.triggered_id == "create-project-button" and create_project_n_clicks:
            #!!TODO: check if project name already exists
            if new_project_name == "" or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$',new_project_name):
                return no_update, no_update, no_update, no_update, no_update, {"display":"block"}, no_update
            else:

                # get the current list of projects from the databse
                projects_db_item = get_db_item(table_name="projects",key_name="username",key_value=username,default_return={"projects":[]})
                curr_projects = projects_db_item["projects"]
                
                # add this new project name to that list
                curr_projects.append(new_project_name)

                # update the projects list in the database with the newly embiggened list
                put_db_item(table_name="projects",key_name="username",key_value=username,item_name="projects",item_value=curr_projects)

                # initialize the class labels so there is one label called "unlabeled" assigned the color black
                # and then put it into the project-classes database for this project
                project_init_classes = [{"name": "unlabeled","color": [0,0,0]}]
                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+new_project_name),item_name="classes",item_value=project_init_classes)

                return populate_files(username,new_project_name), new_project_name, None, "classes_tab", no_update, {"display":"none"}, True
            
        # handle when one of the existing projects is selected - switch to the files tab
        elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'project-card' and not all(n is None for n in project_cards_n_clicks):
            project_name = callback_context.triggered_id["index"]
            logging.debug("SBDEBUG: tab_navigation callback, project selected:"+str(project_name))
            return populate_files(username,project_name), project_name, None, "files_tab", no_update, no_update, no_update
        
        # handle when a new image file is selected - switch to the annotate tab
        elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'file-item':
            filename = callback_context.triggered_id["index"]
            logging.debug("filename %s",filename)
            return no_update, no_update, filename, "annotate_tab", filename, no_update, no_update
        
        # handle when a new file has been uploaded - the list of image files needs to be refresed
        elif callback_context.triggered_id == "upload-notify":
            return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update 
        
        # handle when the refresh button has been clicked on the files tab
        elif callback_context.triggered_id == "refresh-button" and refresh_button_clicks:
            return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update
        
        # something else happened
        elif callback_context.triggered[0]["value"] is None: #!! Do I still need this?
            raise PreventUpdate
        else:
            logging.debug("uncaught trigger in tab_navigation")
            raise PreventUpdate

            



    @app.callback(
        Output({'type': 'label-dropdown', 'index': MATCH}, 'value'),
        Output({'type': 'mask-card', 'index': MATCH}, 'style'),
        Input({'type': 'delete-button', 'index': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def delete_mask_card(n_clicks):
        """
        Callback to handle deleting a mask that has already been saved to the project

        Outputs:
        - label-dropdown: list of all dropdowns associated with mask cards
        - mask-card: list of the style for all mask cards so that we can control their visibility

        Input:
        - delete-button (n_clicks): list of the number of clicks over each of the masks' delete buttons
        """
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
        """
        Callback to handle deleting a mask that has not yet been saved to the project.

        It works the same as delete_mask_card but in the part of the UI where new masks
        are displayed rather than those loaded from the saved project files.
        """
        if not n_clicks is None:
            #logging.debug("deleting mask card",callback_context.triggered_id)
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
        """
        Callback to handle the action of moving a mask to the front in the mask display.

        Outputs:
        - delete-button (n_clicks): Resets the click state of delete buttons (a list).
        - mask-card-move-to-front (data): Data for the mask card to move to the front.
        - mask-move-to-front (data): Data for the mask to move to the front.

        Inputs:
        - front-button (n_clicks): A list of the number of clicks on the 'Front' buttons for masks.

        States:
        - selected-project (selected_project): The name of the currently selected project.
        - selected-image (selected_image_name): The name of the currently selected image.
        - label-dropdown (curr_labels): List of current labels for the masks selected on their dropdowns.
        - new-mask-display (current_new_masks_display): Section of the UI to display of new masks that have not yet been saved.
        """
        logging.debug("front_button_handle triggered with %s",callback_context.triggered_id)
        
        # Check if any of the 'Front' buttons were actually clicked
        if not all(n is None for n in n_clicks):
            #logging.debug("something wasn't None")
            username = get_user_from_session()
            mask_num = callback_context.triggered_id["index"]
            image_obj = SB_project_image(username,selected_project,selected_image_name)

            # Load the image and the mask to move
            image = image_obj.load_image()
            mask_to_move = image_obj.load_masks()[mask_num]

            # Get label options for the project
            label_options = get_label_options(username,selected_project)

            # Create a new mask card for the mask to move
            new_card = create_mask_cards(image,[mask_to_move],[curr_labels[mask_num]],label_options=label_options,new_masks=True,index_offset=len(current_new_masks_display))

            # Reset the click state of the delete buttons
            delete_clicks = [None]*len(n_clicks)
            delete_clicks[mask_num] = 1

            # Return the updated delete clicks, new mask card, and mask to move
            return delete_clicks, new_card, mask_to_move
        return [no_update]*len(n_clicks), no_update, no_update

    @app.callback(
            Output("edit-button-polygon-data","data"),
            Input({'type': 'edit-button', 'index': ALL}, 'n_clicks'),
            State('selected-project','data'),
            State('selected-image','data'),
            prevent_initial_call=True
    )
    def edit_button_handle(n_clicks,selected_project,selected_image_name):
        """
        Callback to handle the action of editing a mask in the selected project and image.
        This takes a mask, converts it to a polygon that is then displayed on the mask-editing UI.
        This allows it to be saved just like a manually-drawn mask.

        Outputs:
        - edit-button-polygon-data (data): The polygon data for the mask we're editing

        Inputs:
        - edit-button (n_clicks): Number of clicks on the 'Edit' buttons for masks (a list).

        States:
        - selected-project (selected_project): The name of the currently selected project.
        - selected-image (selected_image_name): The name of the currently selected image.
        """
        logging.debug("edit_button_handle triggered with %s",callback_context.triggered_id)

        # Check if any of the 'Edit' buttons were actually clicked
        if not all(n is None for n in n_clicks):
            
            username = get_user_from_session()
            mask_num = callback_context.triggered_id["index"]

            # Load the mask to be edited
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            mask_to_edit = image_obj.load_masks()[mask_num]

            # Convert the mask segmentation data into contours
            contours = contours_from_mask(mask_to_edit["segmentation"])

            # Convert contours into polygon shapes suitable for Plotly
            shapes = plotly_shapes_from_contours(contours)

            logging.debug("SHAPES for editing: %s",shapes)
            return shapes
        return no_update

    @app.callback(
        Output('mask-display', 'children'),
        Output('graph-draw','figure'),
        Output('new-mask-display','children'),
        Output('new-mask-store','data'),
        Output("mask-composite-image","src"),
        Output("mask-image","src"),
        
        Input('selected-image','data'),
        Input('generate-manual-mask-button','n_clicks'),
        Input("generate-composite-image-button","n_clicks"),
        Input("mask-card-move-to-front","data"),
        Input({'type': 'new-front-button', 'index': ALL}, 'n_clicks'),
        Input("save-notify",'children'),
        Input("edit-button-polygon-data","data"),

        State('selected-project','data'),
        State('new-mask-store','data'),
        State('new-mask-display','children'),
        State('closed-paths-store','data'),
        State({'type': 'label-dropdown', 'index': ALL}, 'value'),
        State({'type': 'new-label-dropdown', 'index': ALL}, 'value'),
        State("mask-move-to-front","data"),
        State('graph-draw','figure'),
        prevent_initial_call=True
    )
    def update_annotation_page(selected_image_name,generate_manual_n_clicks,gen_composite_n_clicks,new_front_mask_card,nfb_n_clicks,save_notify,edit_button_polygon_data,selected_project,current_new_masks,current_new_display_cards,closed_paths,labels,new_labels,new_front_mask,curr_fig_image):
        """
        Callback to update the annotation page based on various user actions such as selecting an image, generating masks, moving masks, and saving changes.

        Outputs:
        - mask-display (children): The part of the UI where the image masks are displayed.
        - graph-draw (figure): The part of the UI where the user can draw new masks on the image - it is a Plotly figure.
        - new-mask-display (children): The part of the UI where newly generated masks (such as those draw by the user) are displayed - these will be lost if the save button is not clicked.
        - new-mask-store (data): Browser data store for storing newly-generated masks.
        - mask-composite-image (src): The image which is a combination of any labeled masks, drawn partially transparent over the top of the original image.
        - mask-image (src): The combination of labeled masks displayed as an image with the assigned colors - same as above but without the transparency and original image underneath.

        Inputs:
        - selected-image (selected_image_name): The name of the selected image.
        - generate-manual-mask-button (generate_manual_n_clicks): Number of clicks on the button to generate manual mask.
        - generate-composite-image-button (gen_composite_n_clicks): Number of clicks on the button to generate composite images.
        - mask-card-move-to-front (new_front_mask_card): Browser data for a mask card that is moving to the front.
        - new-front-button (nfb_n_clicks): Number of clicks on the front buttons for any newly generated masks (a list).
        - save-notify (save_notify): Whether the notification for a recent save was completed - so everything can be reloaded from the save to ensure consistency.
        - edit-button-polygon-data (edit_button_polygon_data): Browser data store for polygon shapes for masks being edited.

        States:
        - selected-project (selected_project): The name of the currently selected project.
        - new-mask-store (current_new_masks): Browser data for any newly generated masks.
        - new-mask-display (current_new_display_cards): The part of the UI where newly generated masks (such as those draw by the user) are displayed
        - closed-paths-store (closed_paths): Browser data for closed paths (polygons) used in manual mask creation.
        - label-dropdown (labels): Current labels for the masks that were loaded from memory (a list).
        - new-label-dropdown (new_labels): Current labels for any newly generated masks (a list).
        - mask-move-to-front (new_front_mask): Browser data store for the mask to move to the front.
        - graph-draw (curr_fig_image): The Plotly figure where the user may have drawn or edited masks.
        """
        #!!TODO: This is a massive callback because there are so many things that trigger changes to the annotations tab. We should consider decomposing some of the code into utility functions to keep it better organized.
        username = get_user_from_session()
        no_update_ALL = [no_update]*len(nfb_n_clicks)
        logging.debug("update_annotation_page selected_image_name %s",selected_image_name)

        # Handle editing an existing mask
        if callback_context.triggered_id == "edit-button-polygon-data":
            if isinstance(curr_fig_image, dict): #check if the image ends up getting saved as a dict in dcc.Store
                curr_fig_image = go.Figure(curr_fig_image)
            curr_fig_image.update_layout(shapes=edit_button_polygon_data,dragmode="drawclosedpath")
            return no_update, curr_fig_image, no_update, no_update, no_update, no_update
        
        # Handle selecting a new image or completing a save - load everything 
        elif callback_context.triggered_id == "selected-image" or callback_context.triggered_id == "save-notify":
            if not selected_image_name:
                raise PreventUpdate

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

                    segmented_image = ""
                    composite_image = ""
                    if image_obj.has_segmented_image():
                        composite_image, segmented_image = make_composite_image(image,image_obj.load_segmented_image())
                    return display_cards, fig_image, [], None, composite_image, segmented_image #, no_update_ALL
                
                else:
                    
                    logging.debug("loading %s without pre-computed masks",selected_image_name)
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
        
        # Handle when the user clicks the "Generate Manual Mask" button after having
        # drawn on the image with the Plotly closed path tool
        elif callback_context.triggered_id == "generate-manual-mask-button":
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            logging.debug("closed_paths %s",closed_paths)
            new_mask = create_mask_from_paths(closed_paths,image.shape)
            masks_meta = add_meta_info_to_masks([new_mask])
            label_options = get_label_options(username,selected_project)
            #logging.debug("label_options",label_options)
            new_row = create_mask_cards(image,masks_meta,[label_options[0]],label_options=label_options,new_masks=True,index_offset=len(current_new_display_cards))
            new_display_cards = new_row
            if current_new_display_cards:
                new_display_cards += current_new_display_cards
            new_masks_store = masks_meta
            if current_new_masks:
                new_masks_store += current_new_masks
            return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
        

        # Handle a click on the "Generate Composite Mask Image" button
        elif callback_context.triggered_id == "generate-composite-image-button":
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            masks = image_obj.load_masks()
            logging.debug("masks loaded")
            mask_image = np.zeros_like(image)
            label_colors_dict = get_label_colors_dict(username,selected_project)
            
            # loop through the masks from back to front
            for i in range(len(masks)-1,-1,-1):
                
                curr_label = labels[i]
                
                # skip over deleted masks
                if curr_label != "DELETE":
                    curr_mask = np.array(masks[i]["segmentation"])
                    
                    color = label_colors_dict[curr_label]
                    colored_mask = np.zeros_like(image)
                    colored_mask[curr_mask > 0] = color
                    mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

            # check if there are any masks in the "new mask" area and loop through them backwards
            if current_new_masks:
                for i in range(len(current_new_masks)-1,-1,-1):
                    curr_label = new_labels[i]
                    if curr_label != "DELETE":
                        curr_mask = np.array(current_new_masks[i]["segmentation"])
                        color = label_colors_dict[curr_label]
                        colored_mask = np.zeros_like(image)
                        colored_mask[curr_mask > 0] = color
                        mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

            # generate the composite image from the combined mask image and the original image
            composite_image, segmented_image = make_composite_image(image,mask_image)


            return no_update, no_update, no_update, no_update, composite_image, segmented_image #, no_update_ALL
        
        # Handle when the user clicks to move an existing mask to the front
        elif callback_context.triggered_id == "mask-card-move-to-front":
            new_display_cards = new_front_mask_card
            if current_new_display_cards:
                new_display_cards += current_new_display_cards
            new_masks_store = [new_front_mask]
            if current_new_masks:
                new_masks_store += current_new_masks
            return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
        
        # Handle when the user clicks to move a mask in the "new mask" area to the front
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

        logging.debug("uncaught context:  %s",callback_context.triggered_id)
        return no_update, no_update, no_update, no_update, no_update, no_update #, no_update_ALL

    @app.callback(
        Output('drawings-store','data'),
        Output('closed-paths-store','data'),
        Input('graph-draw', 'relayoutData'),
        prevent_initial_call=True
    )
    def update_click_coordinates(shape_data):
        """
        Callback to update the coordinates of manually drawn/edited masks and store the closed paths so
        they can be used by later callbacks

        Outputs:
        - drawings-store (data): List of coordinates for the drawn shapes - TODO: We're not currently using this, but it's here so we can later use non-closed paths for something else (e.g., generating a new SAM mask)
        - closed-paths-store (data): List of closed paths' coordinates - this is what we're using in later callbacks

        Inputs:
        - graph-draw (shape_data): Data from the relayout event of the Plotly figure where the user may have drawn or edited masks.

        Notes:
        - This callback processes different types of shapes (circles and paths) and updates the coordinates accordingly.
        - Closed paths are identified and stored separately.
        """
        logging.debug("shape data  %s",shape_data)


        coords = [] # for non-closed paths
        closed_paths = [] # for closed paths

        # check if we actually have any drawn shapes
        if "shapes" in shape_data:
            for shape in shape_data["shapes"]:

                # in case we use the circle drawing tool later
                if shape["type"] == "circle":
                    include = 1
                    if shape["line"]["color"] == "red":
                        include = 0 
                    x = (shape["x0"]+shape["x1"])/2
                    y = (shape["y0"]+shape["y1"])/2
                    coords.append([include,x,y])

                # check if the user has drawn a path
                if shape["type"] == "path":
                    #check if it is a closed path (format specifies that it ends in "Z")
                    if shape["path"][-1] == "Z":
                        indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                        closed_path_indices = [(float(p[0]),float(p[1])) for p in indices_str]
                        closed_paths.append(closed_path_indices)

                    # in case we later support a non-closed path
                    else:
                        include = 1
                        if shape["line"]["color"] == "red":
                            include = 0 
                        indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                        indices_float = [[include,float(p[0]),float(p[1])] for p in indices_str]
                        
                        coords += indices_float
                        
        # another place closed paths could be
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
