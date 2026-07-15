# Config File

If there is no config.json file in the instance folder, the program will create one with the default values in archivepodcast/config.py.

The default config will not be enough to start the program as you need to define the podcasts you want to archive.

Here is an example with a podcast defined (generated from the pydantic models at docs build time):

```{literalinclude} _generated/example_config.json
:language: json
```
