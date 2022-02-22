
FROM python:3.6
COPY . /ISS_POC
WORKDIR /ISS_POC
RUN pip install -r requirements.txt
CMD ["python", "where_is_the_iss.py", "-i", "10s", "-o", "./ISS_DATA.csv", "-p"]
