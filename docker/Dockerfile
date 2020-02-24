FROM continuumio/miniconda3

ENV ARGS=''

RUN conda install -c openbabel openbabel
RUN conda install -c rdkit rdkit
RUN pip install nanome requests xmltodict

COPY . /app
WORKDIR /app

CMD python run.py ${ARGS}
