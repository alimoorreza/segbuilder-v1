FROM python:3.12.3-alpine3.18

COPY application.py /app/
COPY table_seeder.py /app
COPY user_seeder.py /app
COPY requirements.txt /app
#/app/ additional slash alow docker create dir if doesn't exist
#you need package to download

WORKDIR /app
#sets defult dir

RUN pip3 install -r requirements.txt
# excusting npm install
RUN python3 table_seeder.py
RUN user_seeder.py
RUN aws --endpoint-url=http://localhost:4566 s3 mb s3://segbuilder

CMD ["python3","application"]
