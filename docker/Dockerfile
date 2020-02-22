FROM continuumio/miniconda3

ENV ARGS=''

RUN pip install nanome requests
RUN conda install -c openbabel openbabel

COPY . /app
WORKDIR /app

CMD python run.py ${ARGS}
