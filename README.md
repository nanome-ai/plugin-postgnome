# Nanome - Postgnome

<img src="images/postgnome.png" width="250">

Postgnome allows Nanome users to quickly and easily load data into Nanome from arbitrary sets of web endpoints.

Each configured endpoint, called a Resource, specifies an http request verb, headers, query parameters and post body data to be used when making a request. Additionally, each Resource can be configured to specify how it will import data into Nanome.
Requests consist of one or more Resource firing steps for further flexibility in loading, storing, and passing along web-dependent data. One example of a multistep Request is passing an authorization token loaded from one Resource to another Resource that loads a structure into Nanome.

Additionally, Postgnome allows users to store variables; Resource and Request text fields are allowed to contain variable strings using {{the_variable}} syntax where "the_variable" is the variable's name. This allows the endpoints of Resources to remain independent of Request specific data, such as in https://files.rcsb.org/download/{{structure}}.pdb where "structure" will change depending upon the specific Request being made.

## Dependencies

[Docker](https://docs.docker.com/get-docker/)

## Usage

To run Postgnome in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

## Development

To run Postgnome with autoreload:

```sh
$ python3 -m pip install -r requirements.txt
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

## License

MIT
