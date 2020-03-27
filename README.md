# Nanome - Postgnome 

<img src="images/postgnome.png" width="250">

Postgnome allows Nanome users to quickly and easily load data into Nanome from arbitrary sets of web endpoints.

Each configured endpoint, called a Resource, specifies an http request verb, headers, query parameters and post body data to be used when making a request. Additionally, each Resource can be configured to specify how it will import data into Nanome.
Requests consist of one or more Resource firing steps for further flexibility in loading, storing, and passing along web-dependent data. One example of a multistep Request is passing an authorization token loaded from one Resource to another Resource that loads a structure into Nanome.

Additionally, Postgnome works on a variable system; Resource and Request text fields are allowed to contain variable strings using {{some_variable}} syntax where "some_variable" is the variable's name. This allows the endpoints of Resources to remain independent of Request specific data, such as in https://files.rcsb.org/download/{{structure}}.pdb where "structure" will change depending on the specific Request being made.

### Preparation

Install the latest version of [Python 3](https://www.python.org/downloads/)

| NOTE for Windows: replace `python3` in the following commands with `python` |
| --------------------------------------------------------------------------- |


Install the latest `nanome` lib:

```sh
$ python3 -m pip install nanome --upgrade
```

### Dependencies

**TODO**: Provide instructions on how to install and link any external dependencies for this plugin.

**TODO**: Update docker/Dockerfile to install any necessary dependencies.

### Installation

To install Postgnome:

```sh
$ python3 -m pip install nanome-postgnome
```

### Usage

To start Postgnome:

```sh
$ nanome-postgnome -a <plugin_server_address> [optional args]
```

#### Optional arguments:

- `-x arg`

  Example argument documentation

**TODO**: Add any optional argument documentation here, or remove section entirely.

### Docker Usage

To run Postgnome in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

### Development

To run Postgnome with autoreload:

```sh
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

### License

MIT
