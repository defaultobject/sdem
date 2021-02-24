FROM mongo:4.4.2

# install Python 3
RUN apt-get update && apt-get install -y python3 python3-pip
RUN apt-get -y install python3.7-dev
RUN apt-get -y install git

RUN pip3 install --upgrade pip

COPY requirements.txt .
COPY setup.py .
COPY sdem/ sdem

#run requirements in order
#required because scipy needs numpy to already be installed. see https://stackoverflow.com/questions/51399515/docker-cannot-build-scipy.
RUN while read module; do pip3 install $module; done < requirements.txt

RUN pip3 install dvc[gdrive] 

RUN pip3 install -e .

RUN mkdir ~/.config/
RUN mkdir ~/.config/seml/

RUN touch ~/.config/seml/mongodb.config

RUN  echo  "username: default \n password: default \n port: 27017 \n database: sacred \n host: localhost" >>  ~/.config/seml/mongodb.config

COPY setup_mongo.sh .

EXPOSE 27017

