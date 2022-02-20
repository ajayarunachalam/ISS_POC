FROM python:3.6
docker build https://github.com/ajayarunachalam/ISS_POC
COPY ./ISS_POC /ISS_POC
WORKDIR /ISS_POC
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "where_is_the_iss.py", "-i", "(10s)", "-o", "(./ISS_DATA.csv)", "-p"]