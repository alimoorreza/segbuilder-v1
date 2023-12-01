# segbuilder-v1

# SegBuilder Source Code Local install
 Sean Chen (edited by Alimoor Reza)

## Description
Dr. Manly developed the SegBuilder prototype with remarkable skill, but it seems he did not anticipate others reading his code. Given the time constraints, completely rebuilding the tool would be impractical. Therefore, I recommend running SegBuilder on our own machines for enhanced control over its output. 

Note: The file `Application.py` is the original version received via email and has not been edited.

## How to Run
Follow these steps for successful execution.

## add local endpoint
local endpoint to LocalStack, add the following line in the bracket of every instance of "boto3."
        '''aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566'''

### Virtual Environment
Due to numerous dependencies, it's essential to use a virtual environment to prevent system conflicts.
Download the _SegBuilder_ and unzip it let's say on your desktop. Go to your directory.
```bash
cd ~/Desktop/seg_anything/
```
In the terminal, create the virtual environment:
```bash
python3 -m venv segbuilder_venv
```
This will create a `segbuilder_venv` folder in the base directory.

To activate the virtual environment, in the terminal, enter:
```bash
source segbuilder_venv/bin/activate
```
The beginning of your command line should now display `(segbuilder_venv)`.

**Note:** Ensure that the program is running in the virtual environment to avoid encountering a `ModuleNotFoundError`.

### Download Dependencies

In the terminal, install the required packages:
```bash
pip3 install -r requirements.txt
```
## Docker
Install [docker](https://docs.docker.com/desktop/install/mac-install/) on your MacOSX then
start a docker container


## local stack
Install [local stack](https://github.com/localstack/localstack) using _pip3_. It will be installed on the same directory where you created your virtual environment, i.e., _segbuilder_venv_. Now install __localstack__ as follows using __pip3__:
```bash
python3 -m pip install localstack
```



### DB Table Generation and User Seeding
Run `table_seeder.py` and `user_seeder.py`.

I used ChatGPT to generate Python code based on the schema provided by Eric.

**Note:** It's uncertain how many tables Eric uses for this project;



### Login and Testing
After logging in, the system should function correctly.



**Note:** Login is successful, but the functions have yet to be tested and might be problematic.
it's crazy for pip the dependencies doesn't popout in the project file


## Docker Volume
Create a docker Volume:
        """docker volume create localstack_data"""
Run LocalStack with the Volume Mounted:
        '''docker run -d --name localstack -v localstack_data:/tmp/localstack -p 4566:4566 -p 4571:4571 localstack/localstack'''
Store data with docker 


## (base) lynnre@Lynns-MBP segbuilder_checkpointNov_3_2023 % DATA_DIR=~/Documents/drake/segbuild_data localstack start

(base) lynnre@Lynns-MBP segbuilder_checkpointNov_3_2023 % docker run -e DATA_DIR=~/Documents/drake/segbuild_data -p 4566:4566 localstack/localstack:0.12.20

 aws --endpoint-url=http://localhost:4566 s3 mb s3://segbuilder
