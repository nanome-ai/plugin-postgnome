FROM nanome/plugin-env

ENV ARGS=''

RUN pip install xmltodict
RUN apt-get install nano

ARG CACHEBUST
RUN pip install nanome

COPY . /app
WORKDIR /app

CMD python run.py ${ARGS}
