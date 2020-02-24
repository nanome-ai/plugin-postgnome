FROM continuumio/miniconda3

ENV ARGS=''

RUN pip install nanome requests xmltodict
RUN conda install -c openbabel openbabel

COPY . /app
WORKDIR /app

CMD python run.py ${ARGS}
