FROM python:3.7

RUN mkdir /app
WORKDIR /app
ADD ./src /app/
ADD . /app/
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["tail", "-f" , "/dev/null"]